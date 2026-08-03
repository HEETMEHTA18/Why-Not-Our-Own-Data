"""
Governance feedback loop: benchmark regression closes the loop.

When the BenchmarkAgent records a regression on knowledge the governor
recommended for training, the FeedbackEngine tunes the governor's policy
thresholds so the system learns from its own mistakes:

  - high-novelty-train  novelty floor  raises when LoRA-trained content regresses
  - low-quality-ignore  confidence cap  raises when low-confidence items slipped through
  - api-changes-rag     min_confidence  raises when RAG API knowledge was contradictory
  - security-first      min_confidence  lowers when security items were wrongly RAG'd

Every adjustment emits GOVERNOR_TUNED and is logged so the self-tuning is
fully auditable and reversible.
"""

import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional, List, Dict

from .database.sqlite import SQLiteStore
from .eventbus.bus import get_bus
from .eventbus.models import EventType, EventPriority
from .governor.governor_v2 import KnowledgeGovernor, GOVERNANCE_POLICIES

logger = structlog.get_logger()

DEFAULT_THRESHOLDS = {
    "high-novelty-train": {"novelty_min": 0.8, "max_contradiction": 0.1},
    "low-quality-ignore": {"confidence_max": 0.3},
    "api-changes-rag": {"min_confidence": 0.6},
    "security-first": {"min_confidence": 0.5},
}

STEP_SIZE = 0.05
MAX_STEPS = 8


class FeedbackEngine:
    def __init__(self, db: Optional[SQLiteStore] = None, governor: Optional[KnowledgeGovernor] = None):
        self.db = db or SQLiteStore()
        self.governor = governor or KnowledgeGovernor(self.db)
        self._init_tables()
        self._apply_thresholds()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS governor_tuning_log (
                id TEXT PRIMARY KEY,
                policy TEXT NOT NULL,
                parameter TEXT NOT NULL,
                before_value REAL NOT NULL,
                after_value REAL NOT NULL,
                direction TEXT NOT NULL,
                reason TEXT DEFAULT '',
                regression_task TEXT DEFAULT '',
                tuned_at TEXT NOT NULL
            )
        """)

    def _policy(self, name: str):
        return next((p for p in self.governor.policies if p.name == name), None)

    def _apply_thresholds(self):
        """Restore saved thresholds (from prior tuning) over the static defaults."""
        for policy_name, params in DEFAULT_THRESHOLDS.items():
            policy = self._policy(policy_name)
            if not policy:
                continue
            row = self.db.fetchone(
                "SELECT parameter, after_value FROM governor_tuning_log "
                "WHERE policy = ? ORDER BY tuned_at DESC LIMIT 1",
                (policy_name,),
            )
            if not row:
                self._set_rule_values(policy, params)
                continue
            self._set_rule_value(policy, row["parameter"], row["after_value"])

    def _set_rule_values(self, policy, params: dict):
        for rule in policy.rules:
            if "min_value" in rule and "novelty_min" in params:
                rule["min_value"] = params["novelty_min"]
            if "max_value" in rule and "confidence_max" in params:
                rule["max_value"] = params["confidence_max"]
            if "max_contradiction" in rule and "max_contradiction" in params:
                rule["max_contradiction"] = params["max_contradiction"]
            if "min_confidence" in rule and "min_confidence" in params:
                rule["min_confidence"] = params["min_confidence"]

    def _set_rule_value(self, policy, parameter: str, value: float):
        for rule in policy.rules:
            if parameter == "novelty_min" and "min_value" in rule:
                rule["min_value"] = value
            if parameter == "confidence_max" and "max_value" in rule:
                rule["max_value"] = value
            if parameter == "max_contradiction" and "max_contradiction" in rule:
                rule["max_contradiction"] = value
            if parameter == "min_confidence" and "min_confidence" in rule:
                rule["min_confidence"] = value

    def _current_value(self, policy, parameter: str) -> float:
        for rule in policy.rules:
            if parameter == "novelty_min" and "min_value" in rule:
                return rule["min_value"]
            if parameter == "confidence_max" and "max_value" in rule:
                return rule["max_value"]
            if parameter == "max_contradiction" and "max_contradiction" in rule:
                return rule["max_contradiction"]
            if parameter == "min_confidence" and "min_confidence" in rule:
                return rule["min_confidence"]
        return DEFAULT_THRESHOLDS.get(policy.name, {}).get(parameter, 0.5)

    def record_regression(self, task: str, delta_score: float, knowledge_type: str = "") -> dict:
        """
        Adjust governor thresholds based on a benchmark regression.
        delta_score < 0 means the trained adapter got worse than baseline.
        """
        adjustments = []
        if delta_score >= 0:
            return {"adjusted": 0, "adjustments": adjustments, "reason": "no regression"}

        mag = abs(delta_score)
        if knowledge_type in ("security", "bug_fix"):
            r = self._adjust("security-first", "min_confidence", -1, task, mag,
                             "security knowledge regressed despite high confidence")
            if r:
                adjustments.append(r)
        else:
            for policy, param, direction, reason in [
                ("high-novelty-train", "novelty_min", +1,
                 "novelty-driven LoRA regressed; raise novelty bar"),
                ("api-changes-rag", "min_confidence", +1,
                 "API knowledge contradicted after storage; tighten confidence"),
                ("low-quality-ignore", "confidence_max", +1,
                 "low-confidence items slipped into training; raise ignore bar"),
                ("high-novelty-train", "max_contradiction", -1,
                 "contradictory novel items caused regression; lower tolerance"),
            ]:
                r = self._adjust(policy, param, direction, task, mag, reason)
                if r:
                    adjustments.append(r)

        return {"adjusted": len(adjustments), "adjustments": adjustments,
                "reason": f"regression of {delta_score} on {task}"}

    def _adjust(self, policy_name: str, parameter: str, direction: int,
                task: str, magnitude: float, reason: str) -> Optional[dict]:
        policy = self._policy(policy_name)
        if not policy:
            return None
        current = self._current_value(policy, parameter)

        steps = min(MAX_STEPS, max(1, int(magnitude * 10)))
        new_val = round(current + direction * STEP_SIZE * steps, 3)
        new_val = max(0.0, min(1.0, new_val))
        if abs(new_val - current) < 0.001:
            return None

        self._set_rule_value(policy, parameter, new_val)
        row = {
            "policy": policy_name,
            "parameter": parameter,
            "before": current,
            "after": new_val,
            "direction": "up" if direction > 0 else "down",
            "reason": reason,
            "task": task,
        }
        self.db.execute(
            """INSERT INTO governor_tuning_log
               (id, policy, parameter, before_value, after_value, direction, reason, regression_task, tuned_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), policy_name, parameter, current, new_val,
             row["direction"], reason, task, datetime.now(timezone.utc).isoformat()),
        )

        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                EventType.GOVERNOR_TUNED, "feedback_engine",
                payload={"policy": policy_name, "parameter": parameter,
                         "before": current, "after": new_val},
                priority=EventPriority.LOW,
            ))
        except RuntimeError:
            pass

        logger.info("governor_tuned", policy=policy_name, parameter=parameter,
                    before=current, after=new_val, task=task)
        return row

    def reset_to_defaults(self) -> int:
        for policy_name, params in DEFAULT_THRESHOLDS.items():
            policy = self._policy(policy_name)
            if policy:
                self._set_rule_values(policy, params)
        self.db.execute("DELETE FROM governor_tuning_log")
        logger.info("governor_thresholds_reset")
        return len(DEFAULT_THRESHOLDS)

    def get_current_thresholds(self) -> dict:
        result = {}
        for policy_name, params in DEFAULT_THRESHOLDS.items():
            policy = self._policy(policy_name)
            if not policy:
                continue
            result[policy_name] = {}
            for param in params:
                result[policy_name][param] = self._current_value(policy, param)
        return result

    def get_tuning_history(self, limit: int = 50) -> List[dict]:
        return self.db.fetchall(
            "SELECT * FROM governor_tuning_log ORDER BY tuned_at DESC LIMIT ?", (limit,)
        )

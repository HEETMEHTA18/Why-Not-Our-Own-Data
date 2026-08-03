import uuid
import json
import numpy as np
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from ..database.sqlite import SQLiteStore
from ..config import settings
from .conditions import ConditionChecker
from .models import TrainingRecommendation, GovernorDecision
from .models_v2 import (
    GovernanceAction, GovernanceFactor, KnowledgeItemGovernance,
    GovernancePolicy, TrainingGovernanceSummary
)
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority

import structlog
logger = structlog.get_logger()


GOVERNANCE_POLICIES = [
    GovernancePolicy(
        name="security-first",
        description="Security knowledge always gets stored or trained. Never ignored.",
        rules=[{"factor": "knowledge_type", "values": ["security", "bug_fix"], "action": "recommend_lora", "min_confidence": 0.5}],
        priority=100,
    ),
    GovernancePolicy(
        name="api-changes-rag",
        description="API updates and deprecations go to RAG, not into model weights.",
        rules=[{"factor": "knowledge_type", "values": ["api_update", "deprecation"], "action": "store_rag", "min_confidence": 0.6}],
        priority=80,
    ),
    GovernancePolicy(
        name="high-novelty-train",
        description="Highly novel knowledge that doesn't contradict existing data should be trained.",
        rules=[{"factor": "novelty", "min_value": 0.8, "action": "recommend_lora", "max_contradiction": 0.1}],
        priority=60,
    ),
    GovernancePolicy(
        name="low-quality-ignore",
        description="Low quality or uncertain knowledge should be ignored.",
        rules=[{"factor": "confidence", "max_value": 0.3, "action": "ignore"}],
        priority=90,
    ),
    GovernancePolicy(
        name="framework-patterns-kg",
        description="Framework architecture knowledge belongs in the knowledge graph.",
        rules=[{"factor": "knowledge_type", "values": ["architecture", "framework", "best_practice"], "action": "store_kg", "min_confidence": 0.5}],
        priority=70,
    ),
]


class KnowledgeGovernor:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.policies = GOVERNANCE_POLICIES
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_governance_log (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                factors TEXT DEFAULT '{}',
                alternative_actions TEXT DEFAULT '[]',
                governed_at TEXT NOT NULL,
                applied INTEGER DEFAULT 0
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_gov_knowledge ON knowledge_governance_log(knowledge_id)
        """)

    def govern_knowledge_item(self, knowledge_id: str, text: str, title: str = "",
                               knowledge_type: str = "", confidence: float = 0.0,
                               metadata: dict = None) -> KnowledgeItemGovernance:
        factors = self._compute_factors(knowledge_id, text, title, knowledge_type, confidence, metadata or {})
        action, reason = self._apply_policies(factors)
        alternatives = self._compute_alternatives(factors, action)

        governance = KnowledgeItemGovernance(
            knowledge_id=knowledge_id,
            action=action,
            confidence=factors.get("decision_confidence", 0.5),
            reasoning=reason,
            factors=factors,
            alternative_actions=alternatives,
            governed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._persist(governance)

        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                EventType.KNOWLEDGE_GOVERNED, "knowledge_governor",
                payload={"knowledge_id": knowledge_id, "action": action.value, "confidence": governance.confidence},
                priority=EventPriority.MEDIUM,
            ))
        except RuntimeError:
            pass

        return governance

    def _compute_factors(self, knowledge_id: str, text: str, title: str,
                          knowledge_type: str, confidence: float, metadata: dict) -> dict:
        factors = {}
        text_lower = (title + " " + text).lower()

        factors["knowledge_type"] = knowledge_type or "unknown"
        factors["confidence"] = confidence
        factors["word_count"] = len(text.split())
        factors["has_code"] = 1 if ("```" in text or "def " in text or "function " in text) else 0

        novelty = self._estimate_novelty(knowledge_id, text)
        factors["novelty"] = novelty

        authority = self._estimate_authority(metadata)
        factors["authority"] = authority

        security_terms = ["cve", "vulnerability", "security", "exploit", "patch", "attack", "breach"]
        factors["security_relevance"] = min(1.0, sum(1 for t in security_terms if t in text_lower) * 0.2)

        contradiction_risk = self._estimate_contradiction_risk(text)
        factors["contradiction_risk"] = contradiction_risk

        forgetting_risk = 0.3 if knowledge_type in ("api_update", "deprecation") else 0.1
        factors["forgetting_risk"] = forgetting_risk

        specialization = self._estimate_specialization(text_lower)
        factors["specificity"] = specialization

        difficulty = min(1.0, len(text.split()) / 500)
        factors["complexity"] = round(difficulty, 4)

        weights = {
            "knowledge_type": 0.20, "novelty": 0.15, "confidence": 0.15,
            "authority": 0.10, "security_relevance": 0.10, "contradiction_risk": 0.10,
            "specificity": 0.08, "complexity": 0.07, "has_code": 0.05,
        }
        decision_confidence = sum(
            weights.get(k, 0) * v for k, v in factors.items() if isinstance(v, (int, float))
        )
        factors["decision_confidence"] = round(min(1.0, decision_confidence), 4)

        return factors

    def _estimate_novelty(self, knowledge_id: str, text: str) -> float:
        similar = self.db.fetchall(
            "SELECT output FROM dataset_examples ORDER BY created_at DESC LIMIT 20"
        )
        if not similar:
            return 0.9
        text_lower = text.lower()[:200]
        min_similarity = 1.0
        for row in similar:
            other = (row.get("output") or "")[:200].lower()
            common = len(set(text_lower.split()) & set(other.split()))
            total = len(set(text_lower.split()) | set(other.split()))
            sim = common / max(total, 1)
            min_similarity = min(min_similarity, sim)
        return round(1.0 - min_similarity, 4)

    def _estimate_authority(self, metadata: dict) -> float:
        score = 0.3
        source = (metadata.get("source") or "").lower()
        if "github" in source:
            score += 0.2
        if "arxiv" in source:
            score += 0.3
        if "docs.python" in source or "docs." in source:
            score += 0.2
        if "changelog" in source:
            score += 0.1
        if metadata.get("author"):
            score += 0.1
        if metadata.get("published"):
            score += 0.1
        return min(1.0, score)

    def _estimate_contradiction_risk(self, text: str) -> float:
        existing = self.db.fetchall(
            "SELECT instruction, output FROM dataset_examples WHERE is_valid = 1 ORDER BY RANDOM() LIMIT 10"
        )
        if not existing:
            return 0.0
        text_lower = text.lower()
        conflicts = 0
        for row in existing:
            instr = (row.get("instruction") or "").lower()
            other = (row.get("output") or "").lower()
            if instr and instr.split()[0] in text_lower:
                common = len(set(text_lower.split()) & set(other.split()))
                total = len(set(text_lower.split()) | set(other.split()))
                if total > 0 and common / total < 0.1:
                    conflicts += 1
        return round(conflicts / max(len(existing), 1), 4)

    def _estimate_specialization(self, text: str) -> float:
        domain_terms = {
            "python": ["def ", "import ", "class ", "print(", "lambda", "yield"],
            "javascript": ["function", "const ", "let ", "=>", "console"],
            "typescript": [": string", ": number", "interface", "type "],
            "react": ["component", "usestate", "useeffect", "jsx", "props"],
            "fastapi": ["fastapi", "app.get", "app.post", "depends", "query"],
            "docker": ["docker", "container", "image", "dockerfile", "compose"],
            "kubernetes": ["k8s", "pod", "deployment", "service", "cluster"],
            "sql": ["select", "from ", "where ", "join ", "insert"],
            "rust": ["fn ", "let mut", "impl ", "cargo"],
        }
        found = []
        for domain, terms in domain_terms.items():
            if any(t in text for t in terms):
                found.append(domain)
        return round(min(1.0, len(found) * 0.15), 4)

    def _apply_policies(self, factors: dict) -> Tuple[GovernanceAction, str]:
        sorted_policies = sorted(self.policies, key=lambda p: p.priority, reverse=True)

        for policy in sorted_policies:
            if not policy.active:
                continue
            all_match = True
            reasons = []
            for rule in policy.rules:
                factor = rule.get("factor", "")
                value = factors.get(factor)
                if value is None:
                    all_match = False
                    break
                if "values" in rule:
                    if isinstance(value, str) and value not in rule["values"]:
                        all_match = False
                        break
                    reasons.append(f"{factor}={value} in {rule['values']}")
                if "min_value" in rule:
                    if isinstance(value, (int, float)) and value < rule["min_value"]:
                        all_match = False
                        break
                    reasons.append(f"{factor}={value} >= {rule['min_value']}")
                if "max_value" in rule:
                    if isinstance(value, (int, float)) and value > rule["max_value"]:
                        all_match = False
                        break
                    reasons.append(f"{factor}={value} <= {rule['max_value']}")
                confidence = factors.get("confidence", 0)
                if "min_confidence" in rule and confidence < rule["min_confidence"]:
                    all_match = False
                    break
                if "max_confidence" in rule and confidence > rule["max_confidence"]:
                    all_match = False
                    break
                if "min_contradiction" in rule and factors.get("contradiction_risk", 0) < rule["min_contradiction"]:
                    all_match = False
                    break
                if "max_contradiction" in rule and factors.get("contradiction_risk", 0) > rule["max_contradiction"]:
                    all_match = False
                    break
            if all_match:
                action = GovernanceAction(rule.get("action", "store_rag"))
                return action, f"Policy '{policy.name}': {'; '.join(reasons)}"

        if factors.get("has_code", 0) and factors.get("novelty", 0) > 0.6:
            return GovernanceAction.RECOMMEND_LORA, "High novelty code content — recommended for fine-tuning"
        if factors.get("confidence", 0) < 0.4:
            return GovernanceAction.IGNORE, "Low confidence — insufficient signal for storage or training"
        if factors.get("knowledge_type") in ("api_update", "deprecation"):
            return GovernanceAction.STORE_RAG, "API knowledge best stored in retrieval (RAG), not model weights"
        if factors.get("security_relevance", 0) > 0.5:
            return GovernanceAction.RECOMMEND_LORA, "Security-critical knowledge should be in model weights"

        return GovernanceAction.STORE_RAG, "Default: store in RAG for retrieval-augmented generation"

    def _compute_alternatives(self, factors: dict, chosen: GovernanceAction) -> List[dict]:
        alternatives = []
        for action in GovernanceAction:
            if action == chosen:
                continue
            if action == GovernanceAction.IGNORE:
                if factors.get("confidence", 0) < 0.3:
                    alternatives.append({"action": "ignore", "reason": "Low confidence alternative"})
            elif action == GovernanceAction.STORE_RAG:
                if factors.get("novelty", 0) < 0.9:
                    alternatives.append({"action": "store_rag", "reason": "General-purpose storage"})
            elif action == GovernanceAction.STORE_KG:
                if factors.get("knowledge_type") in ("framework", "architecture", "best_practice"):
                    alternatives.append({"action": "store_kg", "reason": "Relational knowledge fit"})
            elif action == GovernanceAction.RECOMMEND_LORA:
                if factors.get("has_code", 0) and factors.get("novelty", 0) > 0.5:
                    alternatives.append({"action": "recommend_lora", "reason": "Code pattern worth learning"})
        return alternatives[:3]

    def _persist(self, governance: KnowledgeItemGovernance):
        self.db.execute(
            """INSERT OR REPLACE INTO knowledge_governance_log
               (id, knowledge_id, action, confidence, reasoning, factors, alternative_actions, governed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), governance.knowledge_id, governance.action.value,
             governance.confidence, governance.reasoning,
             json.dumps(governance.factors), json.dumps(governance.alternative_actions),
             governance.governed_at),
        )

    def govern_batch(self, items: List[Dict]) -> List[KnowledgeItemGovernance]:
        return [self.govern_knowledge_item(**item) for item in items]

    def evaluate_training_readiness(self) -> TrainingGovernanceSummary:
        total = self.db.fetchone(
            "SELECT COUNT(*) as c FROM knowledge_governance_log WHERE action = 'recommend_lora' AND applied = 0"
        )["c"]
        avg_q = self.db.fetchone(
            "SELECT COALESCE(AVG(confidence), 0) as a FROM knowledge_governance_log WHERE action = 'recommend_lora' AND applied = 0"
        )["a"]

        existing_recs = self.db.fetchone(
            "SELECT COUNT(*) as c FROM training_recommendations WHERE status = 'pending'"
        )["c"]

        lora_items = self.db.fetchall(
            "SELECT reasoning FROM knowledge_governance_log WHERE action = 'recommend_lora' AND applied = 0 LIMIT 5"
        )
        breakdown = {
            "items_pending_governance": self.db.fetchone("SELECT COUNT(*) as c FROM extracted_knowledge")["c"],
            "governed_for_lora": total,
            "existing_pending_recommendations": existing_recs,
            "avg_governance_confidence": round(avg_q, 4),
            "sample_reasonings": [r["reasoning"] for r in lora_items],
        }

        if total < settings.min_examples_for_training:
            return TrainingGovernanceSummary(
                recommend=False,
                reason=f"Only {total} items queued for LoRA training. Need {settings.min_examples_for_training}.",
                example_count=total, avg_quality=round(avg_q, 4),
                estimated_improvement=0, estimated_duration_min=0,
                expected_gain_description="Insufficient data for meaningful training.",
                gpu_usage_estimate="N/A",
                breakdown=breakdown,
            )

        improvement = min(15.0, (avg_q * 0.6 + min(total / 200, 1.0) * 0.4) * 100)
        duration = max(5, int(total / 10))
        gain_desc = f"Expected {improvement:.1f}% loss reduction from {total} governed high-quality examples"
        gpu_est = f"{'Medium' if total < 100 else 'High'} — ~{duration} min on RTX 4050 6GB"

        return TrainingGovernanceSummary(
            recommend=True,
            reason=f"{total} high-confidence knowledge items ready for LoRA fine-tuning.",
            example_count=total,
            avg_quality=round(avg_q, 4),
            estimated_improvement=round(improvement, 2),
            estimated_duration_min=duration,
            expected_gain_description=gain_desc,
            gpu_usage_estimate=gpu_est,
            breakdown=breakdown,
        )

    def mark_applied(self, knowledge_ids: List[str]):
        for kid in knowledge_ids:
            self.db.execute(
                "UPDATE knowledge_governance_log SET applied = 1 WHERE knowledge_id = ?", (kid,)
            )

    def get_governance_stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM knowledge_governance_log")["c"]
        by_action = self.db.fetchall(
            "SELECT action, COUNT(*) as cnt FROM knowledge_governance_log GROUP BY action"
        )
        applied = self.db.fetchone("SELECT COUNT(*) as c FROM knowledge_governance_log WHERE applied = 1")["c"]
        return {
            "total_governed": total,
            "by_action": {r["action"]: r["cnt"] for r in by_action},
            "applied": applied,
            "pending_lora": self.db.fetchone(
                "SELECT COUNT(*) as c FROM knowledge_governance_log WHERE action = 'recommend_lora' AND applied = 0"
            )["c"],
        }
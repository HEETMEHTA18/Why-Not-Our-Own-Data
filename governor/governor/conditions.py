from typing import Dict, Any
from ..config import settings
from ..database.sqlite import SQLiteStore


class ConditionChecker:
    def __init__(self, db: SQLiteStore):
        self.db = db

    def check_all(self) -> Dict[str, Any]:
        return {
            "sufficient_examples": self._check_example_count(),
            "quality_above_threshold": self._check_quality(),
            "no_excessive_contradictions": self._check_contradictions(),
            "sufficient_diversity": self._check_diversity(),
            "cooldown_elapsed": self._check_cooldown(),
            "min_duplicate_rate": self._check_duplicates(),
        }

    def _check_example_count(self) -> dict:
        count = self.db.fetchone(
            "SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1"
        )["c"]
        passed = count >= settings.min_examples_for_training
        return {"passed": passed, "count": count, "required": settings.min_examples_for_training}

    def _check_quality(self) -> dict:
        row = self.db.fetchone(
            "SELECT COALESCE(AVG(quality_score), 0) as avg_q FROM dataset_examples WHERE is_valid = 1"
        )
        avg_q = row["avg_q"] if row else 0
        passed = avg_q >= settings.min_quality_for_training
        return {"passed": passed, "avg_quality": round(avg_q, 4), "required": settings.min_quality_for_training}

    def _check_contradictions(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1")["c"]
        if total == 0:
            return {"passed": False, "contradiction_count": 0, "ratio": 0.0, "reason": "no_examples"}
        rows = self.db.fetchall(
            "SELECT instruction, COUNT(DISTINCT output) as variants FROM dataset_examples "
            "WHERE is_valid = 1 GROUP BY instruction HAVING variants > 1"
        )
        contradiction_count = len(rows)
        ratio = contradiction_count / total
        passed = ratio <= settings.max_contradiction_ratio
        return {"passed": passed, "contradiction_count": contradiction_count, "ratio": round(ratio, 4)}

    def _check_diversity(self) -> dict:
        rows = self.db.fetchall("SELECT COUNT(DISTINCT instruction) as unique_instr FROM dataset_examples WHERE is_valid = 1")
        total = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1")["c"]
        unique = rows[0]["unique_instr"] if rows else 0
        diversity = unique / max(total, 1)
        passed = diversity > 0.3
        return {"passed": passed, "unique_instructions": unique, "total": total, "diversity_ratio": round(diversity, 4)}

    def _check_cooldown(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1")["c"]
        if total == 0:
            return {"passed": False, "days_since_last": float("inf"), "reason": "no_examples"}
        last = self.db.fetchone(
            "SELECT recommended_at FROM training_recommendations WHERE status = 'approved' "
            "ORDER BY approved_at DESC LIMIT 1"
        )
        if not last:
            return {"passed": True, "days_since_last": float("inf"), "reason": "no_previous_training"}
        from datetime import datetime, timezone
        last_ts = datetime.fromisoformat(last["recommended_at"])
        now = datetime.now(timezone.utc)
        days = (now - last_ts).total_seconds() / 86400
        passed = days >= settings.training_cooldown_days
        return {"passed": passed, "days_since_last": round(days, 1), "cooldown_days": settings.training_cooldown_days}

    def _check_duplicates(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1")["c"]
        if total == 0:
            return {"passed": False, "duplicate_count": 0, "duplicate_rate": 0.0, "reason": "no_examples"}
        rows = self.db.fetchall(
            "SELECT instruction, COUNT(*) as cnt FROM dataset_examples "
            "WHERE is_valid = 1 GROUP BY instruction HAVING cnt > 1"
        )
        dup_count = sum(r["cnt"] - 1 for r in rows)
        dup_rate = dup_count / total
        passed = dup_rate < 0.3
        return {"passed": passed, "duplicate_count": dup_count, "duplicate_rate": round(dup_rate, 4)}

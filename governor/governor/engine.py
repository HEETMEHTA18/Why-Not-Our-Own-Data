import json
import uuid
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from ..database.sqlite import SQLiteStore
from ..config import settings
from .conditions import ConditionChecker
from .models import TrainingRecommendation, GovernorDecision


class TrainingGovernor:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.checker = ConditionChecker(self.db)

    def evaluate(self) -> GovernorDecision:
        conditions = self.checker.check_all()
        all_passed = all(c["passed"] for c in conditions.values())

        if not all_passed:
            failed = [k for k, v in conditions.items() if not v["passed"]]
            return GovernorDecision(
                recommend=False,
                reason=f"Conditions not met: {', '.join(failed)}",
                details=conditions,
            )

        rec = self._build_recommendation(conditions)
        self._persist_recommendation(rec)

        return GovernorDecision(
            recommend=True,
            reason="All conditions satisfied. Ready for training.",
            details={**conditions, "recommendation": rec.model_dump()},
            recommendation_id=rec.id,
        )

    def _build_recommendation(self, conditions: dict) -> TrainingRecommendation:
        total = self.db.fetchone(
            "SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1"
        )["c"]
        avg_q = conditions["quality_above_threshold"].get("avg_quality", 0)
        contradictions = conditions.get("no_excessive_contradictions", {}).get("contradiction_count", 0)
        duplicates = conditions.get("min_duplicate_rate", {}).get("duplicate_count", 0)
        diversity = conditions.get("sufficient_diversity", {}).get("diversity_ratio", 0)
        days_since = conditions.get("cooldown_elapsed", {}).get("days_since_last", 999)

        estimated_improvement = self._estimate_improvement(avg_q, total, diversity)
        estimated_duration = max(5, int(total / 10))

        return TrainingRecommendation(
            id=str(uuid.uuid4()),
            recommended_at=datetime.now(timezone.utc).isoformat(),
            status="pending",
            example_count=total,
            avg_quality=round(avg_q, 4),
            estimated_improvement=round(estimated_improvement, 2),
            estimated_duration_min=estimated_duration,
            contradiction_count=contradictions,
            duplicate_count=duplicates,
            diversity_score=round(diversity, 4),
            days_since_last_training=round(days_since, 1),
            decision_log={"conditions": {k: v["passed"] for k, v in conditions.items()}},
        )

    def _estimate_improvement(self, avg_quality: float, count: int, diversity: float) -> float:
        base = avg_quality * 0.5
        count_factor = min(count / 200, 1.0) * 0.3
        diversity_factor = diversity * 0.2
        return min(15.0, (base + count_factor + diversity_factor) * 100)

    def _persist_recommendation(self, rec: TrainingRecommendation):
        self.db.execute(
            """INSERT INTO training_recommendations
               (id, recommended_at, status, example_count, avg_quality, estimated_improvement,
                estimated_duration_min, contradiction_count, duplicate_count, diversity_score,
                days_since_last_training, decision_log)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rec.id, rec.recommended_at, rec.status, rec.example_count, rec.avg_quality,
             rec.estimated_improvement, rec.estimated_duration_min, rec.contradiction_count,
             rec.duplicate_count, rec.diversity_score, rec.days_since_last_training,
             json.dumps(rec.decision_log)),
        )

    def approve(self, recommendation_id: str, notes: str = "") -> Optional[TrainingRecommendation]:
        ts = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE training_recommendations SET status = 'approved', approved_at = ?, decision_log = ? WHERE id = ?",
            (ts, json.dumps({"notes": notes, "approved_at": ts}), recommendation_id),
        )
        return self.get_recommendation(recommendation_id)

    def reject(self, recommendation_id: str, notes: str = "") -> Optional[TrainingRecommendation]:
        ts = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE training_recommendations SET status = 'rejected', rejected_at = ?, decision_log = ? WHERE id = ?",
            (ts, json.dumps({"notes": notes, "rejected_at": ts}), recommendation_id),
        )
        return self.get_recommendation(recommendation_id)

    def get_recommendation(self, recommendation_id: str) -> Optional[TrainingRecommendation]:
        row = self.db.fetchone("SELECT * FROM training_recommendations WHERE id = ?", (recommendation_id,))
        if row:
            row["decision_log"] = json.loads(row["decision_log"]) if isinstance(row.get("decision_log"), str) else {}
            return TrainingRecommendation(**row)
        return None

    def list_recommendations(self, status: Optional[str] = None) -> list:
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM training_recommendations WHERE status = ? ORDER BY recommended_at DESC",
                (status,),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM training_recommendations ORDER BY recommended_at DESC"
            )
        for r in rows:
            r["decision_log"] = json.loads(r["decision_log"]) if isinstance(r.get("decision_log"), str) else {}
        return [TrainingRecommendation(**r) for r in rows]

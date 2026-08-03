from typing import Optional
from ..database.sqlite import SQLiteStore
from ..governor.engine import TrainingGovernor
from ..config import settings
from .models import ConsentPrompt, ConsentResponse


class ConsentManager:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.governor = TrainingGovernor(self.db)

    def build_prompt(self, recommendation_id: str) -> Optional[ConsentPrompt]:
        rec = self.governor.get_recommendation(recommendation_id)
        if not rec:
            return None
        return ConsentPrompt(
            recommendation_id=rec.id,
            corrections_count=rec.example_count,
            estimated_improvement=rec.estimated_improvement,
            estimated_duration_min=rec.estimated_duration_min,
            gpu_usage="High" if rec.example_count > 100 else "Medium",
            quality_score=rec.avg_quality,
            dataset_size=rec.example_count,
            message=(
                f"Collected {rec.example_count} validated examples "
                f"(quality: {rec.avg_quality:.0%}). "
                f"Estimated improvement: +{rec.estimated_improvement:.1f}%. "
                f"Duration: ~{rec.estimated_duration_min} min. "
                f"GPU usage: {'High' if rec.example_count > 100 else 'Medium'}. "
                "Proceed?"
            ),
        )

    def record_decision(self, response: ConsentResponse) -> bool:
        if response.decision == "yes":
            self.governor.approve(response.recommendation_id, response.notes)
            return True
        elif response.decision == "later":
            rec = self.governor.get_recommendation(response.recommendation_id)
            if rec:
                self.db.execute(
                    "UPDATE training_recommendations SET status = 'deferred', decision_log = ? WHERE id = ?",
                    (str({"deferred_at": response.timestamp, "notes": response.notes}),
                     response.recommendation_id),
                )
            return False
        else:
            self.governor.reject(response.recommendation_id, response.notes)
            return False

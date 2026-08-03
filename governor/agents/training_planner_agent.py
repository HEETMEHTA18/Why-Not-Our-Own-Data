from typing import Optional
from ..database.sqlite import SQLiteStore
from ..governor.engine import TrainingGovernor
from ..governor.governor_v2 import KnowledgeGovernor
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from .base import BaseAgent
from .models import AgentConfig


class TrainingPlannerAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.governor = TrainingGovernor(db)
        self.knowledge_governor = KnowledgeGovernor(db)

    async def execute(self, context: dict = None) -> dict:
        summary = self.knowledge_governor.evaluate_training_readiness()

        if not summary.recommend:
            existing = self.governor.list_recommendations(status="pending")
            return {
                "recommend_training": False,
                "reason": summary.reason,
                "breakdown": summary.breakdown,
                "pending_recommendations": len(existing),
            }

        decision = self.governor.evaluate()

        await get_bus().publish_sync(
            EventType.TRAINING_RECOMMENDED, "training_planner",
            payload={
                "recommend": summary.recommend,
                "reason": summary.reason,
                "example_count": summary.example_count,
                "estimated_gain": summary.estimated_improvement,
                "recommendation_id": decision.recommendation_id,
            },
            priority=EventPriority.HIGH,
        )

        await get_bus().publish_sync(
            EventType.USER_APPROVAL_REQUIRED, "training_planner",
            payload={
                "recommendation_id": decision.recommendation_id,
                "summary": summary.model_dump(),
                "type": "training_approval",
            },
            priority=EventPriority.CRITICAL,
        )

        return {
            "recommend_training": True,
            "reason": summary.reason,
            "expected_gain": summary.estimated_improvement,
            "estimated_duration": summary.estimated_duration_min,
            "example_count": summary.example_count,
            "avg_quality": summary.avg_quality,
            "gpu_estimate": summary.gpu_usage_estimate,
            "recommendation_id": decision.recommendation_id,
            "breakdown": summary.breakdown,
        }
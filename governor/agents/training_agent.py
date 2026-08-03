from typing import Optional
from ..database.sqlite import SQLiteStore
from ..governor.engine import TrainingGovernor
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from ..config import settings
from .base import BaseAgent
from .models import AgentConfig

import structlog
logger = structlog.get_logger()


class TrainingAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.gov = TrainingGovernor(db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        rec_id = ctx.get("recommendation_id")
        approved = ctx.get("approved", True)

        if rec_id:
            rec = self.gov.get_recommendation(rec_id)
            if not rec:
                return {"status": "failed", "error": f"recommendation {rec_id} not found"}
            if approved:
                self.gov.approve(rec_id, notes="Approved by TrainingPlannerAgent pipeline")
            else:
                self.gov.reject(rec_id, notes="Rejected by TrainingPlannerAgent pipeline")
                return {"status": "rejected", "recommendation_id": rec_id}

            await get_bus().publish_sync(
                EventType.TRAINING_STARTED, "training_agent",
                payload={
                    "recommendation_id": rec_id,
                    "example_count": rec.example_count,
                    "estimated_improvement": rec.estimated_improvement,
                    "estimated_duration": rec.estimated_duration_min,
                },
                priority=EventPriority.HIGH,
            )

            return {
                "status": "ready",
                "recommendation_id": rec_id,
                "example_count": rec.example_count,
                "estimated_improvement": rec.estimated_improvement,
                "estimated_duration_min": rec.estimated_duration_min,
                "dataset_ready": True,
            }

        decision = self.gov.evaluate()
        if not decision.recommend:
            return {"status": "not_ready", "reason": decision.reason}

        if approved:
            self.gov.approve(decision.recommendation_id, notes="Auto-approved by TrainingAgent")
            await get_bus().publish_sync(
                EventType.TRAINING_STARTED, "training_agent",
                payload={"recommendation_id": decision.recommendation_id},
                priority=EventPriority.HIGH,
            )

        return {
            "status": "ready" if approved else "pending_approval",
            "recommendation_id": decision.recommendation_id,
            "recommendation": decision.details.get("recommendation", {}),
        }
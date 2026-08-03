from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..quality.scorer import QualityScorer
from ..dataset.builder import DatasetBuilder
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType
from .base import BaseAgent
from .models import AgentConfig


class QualityAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.scorer = QualityScorer(db)
        self.builder = DatasetBuilder(db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        min_quality = ctx.get("min_quality", 0.7)

        scores = self.scorer.score_all(valid_only=True)
        if not scores:
            return {"status": "completed", "scored": 0, "passed": 0, "rejected": 0}

        passed = [s for s in scores if s.overall >= min_quality]
        rejected = [s for s in scores if s.overall < min_quality]

        stats = self.builder.stats()
        avg_by_dim = {}
        if passed:
            for dim in ["coherence", "correctness", "completeness", "novelty", "confidence", "importance", "consistency", "difficulty"]:
                vals = [getattr(s, dim, 0) for s in passed]
                avg_by_dim[dim] = round(sum(vals) / len(vals), 4)

        await get_bus().publish_sync(
            EventType.DATASET_SCORED, "quality_agent",
            payload={
                "scored": len(scores), "passed": len(passed),
                "rejected": len(rejected), "avg_quality": round(sum(s.overall for s in scores) / len(scores), 4),
            },
        )

        return {
            "scored": len(scores),
            "passed_threshold": len(passed),
            "rejected": len(rejected),
            "avg_quality": round(sum(s.overall for s in scores) / len(scores), 4) if scores else 0,
            "avg_by_dimension": avg_by_dim,
            "dataset_stats": stats,
        }
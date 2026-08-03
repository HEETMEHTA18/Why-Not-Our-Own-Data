from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..governor.governor_v2 import KnowledgeGovernor
from ..extractor.engine import ExtractionEngine
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType
from .base import BaseAgent
from .models import AgentConfig


class DatasetAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.extractor = ExtractionEngine(db)
        self.governor = KnowledgeGovernor(db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        limit = ctx.get("limit", 50)

        unextracted = self.extractor.extract_unextracted(limit=limit)
        if not unextracted:
            return {"status": "completed", "extracted": 0, "governed": 0}

        governed = []
        for knowledge in unextracted:
            g = self.governor.govern_knowledge_item(
                knowledge_id=knowledge.id,
                text=knowledge.output,
                title=knowledge.title,
                knowledge_type=knowledge.knowledge_type.value,
                confidence=knowledge.confidence,
                metadata={
                    "source": knowledge.metadata.get("source", ""),
                    "author": knowledge.metadata.get("author", ""),
                    "published": knowledge.metadata.get("published", ""),
                },
            )
            governed.append(g)

        from ..dataset.builder import DatasetBuilder
        builder = DatasetBuilder(self.db)
        for knowledge in unextracted:
            self.extractor.push_to_dataset(knowledge.id)

        lora_count = sum(1 for g in governed if g.action.value == "recommend_lora")
        rag_count = sum(1 for g in governed if g.action.value == "store_rag")
        kg_count = sum(1 for g in governed if g.action.value == "store_kg")
        ignored = sum(1 for g in governed if g.action.value == "ignore")

        await get_bus().publish_sync(
            EventType.DATASET_BUILT, "dataset_agent",
            payload={
                "extracted": len(unextracted), "governed": len(governed),
                "for_lora": lora_count, "for_rag": rag_count,
                "for_kg": kg_count, "ignored": ignored,
            },
        )

        return {
            "extracted": len(unextracted),
            "governed": len(governed),
            "governance_breakdown": {
                "lora": lora_count, "rag": rag_count,
                "knowledge_graph": kg_count, "ignored": ignored,
            },
        }
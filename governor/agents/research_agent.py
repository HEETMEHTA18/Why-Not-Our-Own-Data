from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..crawler.engine import CrawlerEngine
from ..crawler.models import CrawlRequest, SourceType
from ..extractor.engine import ExtractionEngine
from ..research.engine import ResearchEngine
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from .base import BaseAgent
from .models import AgentConfig, AgentType


class ResearchAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.crawler = CrawlerEngine(db)
        self.extractor = ExtractionEngine(db)
        self.research = ResearchEngine(db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        max_items = ctx.get("max_items", 5)
        since_days = ctx.get("since_days", 7)

        sources = ctx.get("sources", ["github_release", "arxiv_paper", "changelog"])

        all_crawled = []
        for src_name in sources:
            try:
                src = SourceType(src_name)
                req = CrawlRequest(source=src, max_items=max_items, since_days=since_days)
                items = await self.crawler.crawl(req)
                all_crawled.extend(items)
            except Exception as e:
                continue

        extracted = self.extractor.extract_many(all_crawled)
        self.research.seed_topics()

        paper_count = len([i for i in all_crawled if i.source == SourceType.ARXIV_PAPER])
        extracted_count = len(extracted)

        await get_bus().publish_sync(
            EventType.RESEARCH_FINDING, "research_agent",
            payload={"crawled": len(all_crawled), "extracted": extracted_count, "papers": paper_count},
            priority=EventPriority.LOW,
        )

        return {
            "crawled": len(all_crawled),
            "extracted": extracted_count,
            "papers_found": paper_count,
            "sources_used": sources,
            "status": "completed",
        }
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..crawler.engine import CrawlerEngine
from ..crawler.models import CrawlRequest, SourceType
from ..extractor.engine import ExtractionEngine
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType
from .base import BaseAgent
from .models import AgentConfig


class DocumentationAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)
        self.crawler = CrawlerEngine(db)
        self.extractor = ExtractionEngine(db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        since_days = ctx.get("since_days", 1)
        repos = ctx.get("repos", None)
        doc_urls = ctx.get("doc_urls", None)

        releases = await self.crawler.crawl(CrawlRequest(
            source=SourceType.GITHUB_RELEASE,
            max_items=20,
            since_days=since_days,
            urls=repos,
        ))

        docs = await self.crawler.crawl(CrawlRequest(
            source=SourceType.OFFICIAL_DOCS,
            max_items=10,
            since_days=since_days,
            urls=doc_urls,
        ))

        extracted = self.extractor.extract_many(releases + docs)

        api_updates = [e for e in extracted if e.knowledge_type.value == "api_update"]
        deprecations = [e for e in extracted if e.knowledge_type.value == "deprecation"]
        security = [e for e in extracted if e.knowledge_type.value == "security"]

        await get_bus().publish_sync(
            EventType.DOCUMENTATION_UPDATE, "doc_agent",
            payload={
                "releases": len(releases), "docs": len(docs),
                "api_updates": len(api_updates), "deprecations": len(deprecations),
                "security": len(security),
            },
        )

        return {
            "releases_checked": len(releases),
            "docs_scraped": len(docs),
            "extracted": len(extracted),
            "api_updates": len(api_updates),
            "deprecations": len(deprecations),
            "security_advisories": len(security),
        }
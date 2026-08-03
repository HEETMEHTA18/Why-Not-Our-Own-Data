from fastapi import APIRouter, Query
from .models import CrawlRequest, CrawledItem
from .engine import CrawlerEngine

router = APIRouter(prefix="/crawl", tags=["crawler"])
engine = CrawlerEngine()


@router.post("/run")
async def run_crawl(req: CrawlRequest):
    items = await engine.crawl(req)
    return {"source": req.source.value, "items_crawled": len(items), "items": [i.model_dump() for i in items]}


@router.post("/run-all")
async def run_all(max_per_source: int = 5):
    items = await engine.crawl_all_sources(max_per_source=max_per_source)
    return {"items_crawled": len(items)}


@router.get("/items")
def list_items(source: str = None, limit: int = 50, offset: int = 0):
    items = engine.list_items(source=source, limit=limit, offset=offset)
    return {"total": len(items), "items": [i.model_dump() for i in items]}


@router.get("/stats")
def get_stats():
    return engine.stats()


@router.get("/unextracted")
def get_unextracted(limit: int = 50):
    items = engine.get_unextracted(limit=limit)
    return {"total": len(items), "items": [i.model_dump() for i in items]}

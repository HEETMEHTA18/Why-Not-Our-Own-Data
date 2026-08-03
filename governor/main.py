from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .collector.router import router as collector_router
from .dataset.router import router as dataset_router
from .quality.router import router as quality_router
from .memory.router import router as memory_router
from .governor.router import router as governor_router
from .governor.router_v2 import router as governor_v2_router
from .consent.router import router as consent_router
from .crawler.router import router as crawler_router
from .extractor.router import router as extractor_router
from .classifier.router import router as classifier_router
from .research.router import router as research_router
from .experiments.router import router as experiments_router
from .eventbus.router import router as events_router
from .agents.router import router as agents_router
from .knowledge_graph.router import router as kg_router
from .benchmarks.router import router as benchmarks_router
from .scheduler_router import router as scheduler_router
from .platform_router import router as platform_router
from .rag.router import router as rag_router
from .eventbus.bus import get_bus


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = get_bus()
    bus.start()
    yield
    await bus.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Data Intelligence & Governance Engine for Tatvik AI — with Agent Orchestration",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(collector_router)
app.include_router(dataset_router)
app.include_router(quality_router)
app.include_router(memory_router)
app.include_router(governor_router)
app.include_router(governor_v2_router)
app.include_router(consent_router)
app.include_router(crawler_router)
app.include_router(extractor_router)
app.include_router(classifier_router)
app.include_router(research_router)
app.include_router(experiments_router)
app.include_router(events_router)
app.include_router(agents_router)
app.include_router(kg_router)
app.include_router(benchmarks_router)
app.include_router(scheduler_router)
app.include_router(platform_router)
app.include_router(rag_router)


@app.get("/health")
def health():
    bus = get_bus()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "event_bus": bus.get_stats().model_dump(),
    }


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "endpoints": {
            "collect": "/collect/*",
            "dataset": "/dataset/*",
            "quality": "/quality/*",
            "memory": "/memory/*",
            "governor": "/governor/*",
            "consent": "/consent/*",
            "crawl": "/crawl/*",
            "extract": "/extract/*",
            "classify": "/classify/*",
            "research": "/research/*",
            "experiments": "/experiments/*",
            "events": "/events/*",
            "agents": "/agents/*",
            "knowledge_graph": "/kg/*",
            "benchmarks": "/benchmarks/*",
            "scheduler": "/scheduler/*",
            "platform": "/platform/*",
            "rag": "/rag/*",
        },
    }

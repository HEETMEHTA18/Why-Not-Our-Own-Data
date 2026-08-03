from __future__ import annotations
import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from .orchestrator import get_hermes
from .config import settings

logger = structlog.get_logger()


class RunAgentRequest(BaseModel):
    agent_id: str
    context: dict = {}


class RunPipelineRequest(BaseModel):
    pipeline_name: str
    context: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    hermes = get_hermes()
    await hermes.initialize()
    logger.info("hermes_api_started", host=settings.host, port=settings.port)
    yield
    if hermes.bus._running:
        await hermes.bus.stop()


app = FastAPI(
    title="Hermes Orchestrator API",
    version="0.1.0",
    description="Multi-Agent Orchestration Layer for autonomous AI fine-tuning",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    h = get_hermes()
    s = h.get_status()
    return {"status": s["status"], "agents": len(s["agents"]), "event_bus": s["event_bus"], "service": "hermes"}


@app.get("/")
def root():
    return {
        "service": "Hermes Orchestrator",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "agents": "/agents (GET list, POST run)",
            "pipelines": "/pipelines (GET list, POST run)",
            "runs": "/runs (GET history)",
        },
    }


@app.get("/status")
def status():
    h = get_hermes()
    return h.get_status()


@app.get("/agents")
def list_agents():
    h = get_hermes()
    return {"agents": h.get_status()["agents"]}


@app.post("/agents/run")
async def run_agent(req: RunAgentRequest):
    h = get_hermes()
    if not h._initialized:
        await h.initialize()
    try:
        result = await h.run_agent(req.agent_id, req.context)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/agents/run-all")
async def run_all_agents():
    h = get_hermes()
    if not h._initialized:
        await h.initialize()
    results = []
    for aid in h._agents:
        r = await h.run_agent(aid)
        results.append(r)
    return {"results": results}


@app.get("/pipelines")
def list_pipelines():
    h = get_hermes()
    return {"pipelines": h.get_status()["pipelines"]}


@app.post("/pipelines/run")
async def run_pipeline(req: RunPipelineRequest):
    h = get_hermes()
    if not h._initialized:
        await h.initialize()
    try:
        result = await h.run_pipeline(req.pipeline_name, req.context)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/runs")
def get_runs(agent_id: Optional[str] = None, limit: int = 20):
    h = get_hermes()
    return {"runs": h.get_recent_runs(agent_id, limit)}


@app.get("/events/stats")
def event_stats():
    h = get_hermes()
    return {"stats": h.bus.get_stats().model_dump()}


@app.get("/events/recent")
def recent_events(limit: int = 20):
    h = get_hermes()
    events = h.bus.history[-limit:] if hasattr(h.bus, "history") else []
    return {"events": [e.model_dump() for e in events]}
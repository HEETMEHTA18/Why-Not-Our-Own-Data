from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .base import AgentOrchestrator, BaseAgent
from .models import AgentConfig, AgentType
from .research_agent import ResearchAgent
from .documentation_agent import DocumentationAgent
from .dataset_agent import DatasetAgent
from .quality_agent import QualityAgent
from .training_planner_agent import TrainingPlannerAgent
from .training_agent import TrainingAgent
from .benchmark_agent import BenchmarkAgent
from .deployment_agent import DeploymentAgent
from ..database.sqlite import SQLiteStore

router = APIRouter(prefix="/agents", tags=["agents"])

_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        db = SQLiteStore()
        _orchestrator = AgentOrchestrator(db)
        _register_default_agents(_orchestrator, db)
    return _orchestrator


def _register_default_agents(orchestrator: AgentOrchestrator, db: SQLiteStore):
    agents = [
        AgentConfig(agent_id="research-1", agent_type=AgentType.RESEARCH,
                    name="Research Agent", description="Reads papers, releases, changelogs",
                    interval_minutes=1440),
        AgentConfig(agent_id="doc-1", agent_type=AgentType.DOCUMENTATION,
                    name="Documentation Agent", description="Monitors API docs and changelogs",
                    interval_minutes=60),
        AgentConfig(agent_id="dataset-1", agent_type=AgentType.DATASET,
                    name="Dataset Agent", description="Builds datasets from extracted knowledge",
                    interval_minutes=30),
        AgentConfig(agent_id="quality-1", agent_type=AgentType.QUALITY,
                    name="Quality Agent", description="Scores dataset quality",
                    interval_minutes=30),
        AgentConfig(agent_id="planner-1", agent_type=AgentType.TRAINING_PLANNER,
                    name="Training Planner", description="Decides when training is needed",
                    interval_minutes=60),
        AgentConfig(agent_id="trainer-1", agent_type=AgentType.TRAINING,
                    name="Training Agent", description="Executes LoRA fine-tuning pipeline",
                    interval_minutes=0),
        AgentConfig(agent_id="bench-1", agent_type=AgentType.BENCHMARK,
                    name="Benchmark Agent", description="Runs model benchmarks",
                    interval_minutes=0),
        AgentConfig(agent_id="deploy-1", agent_type=AgentType.DEPLOYMENT,
                    name="Deployment Agent", description="Validates and deploys adapters",
                    interval_minutes=0),
    ]
    for cfg in agents:
        cls_map = {
            AgentType.RESEARCH: ResearchAgent,
            AgentType.DOCUMENTATION: DocumentationAgent,
            AgentType.DATASET: DatasetAgent,
            AgentType.QUALITY: QualityAgent,
            AgentType.TRAINING_PLANNER: TrainingPlannerAgent,
            AgentType.TRAINING: TrainingAgent,
            AgentType.BENCHMARK: BenchmarkAgent,
            AgentType.DEPLOYMENT: DeploymentAgent,
        }
        agent_cls = cls_map.get(cfg.agent_type)
        if agent_cls:
            orchestrator.register_agent(agent_cls(cfg, db))


@router.get("/")
def list_agents():
    orch = get_orchestrator()
    return {"agents": orch.list_agents()}


@router.post("/{agent_id}/run")
async def run_agent(agent_id: str):
    orch = get_orchestrator()
    agent = orch.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    run = await agent.run()
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "result": run.result,
        "error": run.error,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


class RunPipelineRequest(BaseModel):
    name: str
    context: dict = {}


class CreatePipelineRequest(BaseModel):
    name: str
    steps: list
    description: str = ""


@router.post("/pipeline/run")
async def run_pipeline(req: RunPipelineRequest):
    orch = get_orchestrator()
    results = await orch.run_pipeline(req.name, req.context)
    return {"pipeline": req.name, "results": results}


@router.post("/pipeline/create")
def create_pipeline(req: CreatePipelineRequest):
    orch = get_orchestrator()
    orch.create_pipeline(req.name, req.steps, req.description)
    return {"created": True, "name": req.name, "steps": len(req.steps)}


@router.get("/pipeline/list")
def list_pipelines():
    orch = get_orchestrator()
    rows = orch.db.fetchall("SELECT name, description, active FROM pipeline_definitions")
    return {"pipelines": rows}


@router.get("/pipeline/{name}")
def get_pipeline(name: str):
    orch = get_orchestrator()
    row = orch.db.fetchone(
        "SELECT * FROM pipeline_definitions WHERE name = ?", (name,)
    )
    if not row:
        raise HTTPException(404, f"Pipeline {name} not found")
    row["steps"] = eval(row["steps"])
    return row


@router.get("/runs")
def list_runs(agent_id: str = None, limit: int = 20):
    orch = get_orchestrator()
    if agent_id:
        agent = orch.get_agent(agent_id)
        if not agent:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return {"runs": agent.get_recent_runs(limit)}
    rows = orch.db.fetchall(
        "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?", (limit,)
    )
    for r in rows:
        r["result"] = eval(r.get("result", "{}"))
    return {"runs": rows}


@router.post("/initialize-pipelines")
def init_default_pipelines():
    orch = get_orchestrator()

    daily_research = {
        "name": "daily-research",
        "steps": [
            {"agent_id": "research-1", "params": {"since_days": 1}},
            {"agent_id": "doc-1", "params": {"since_days": 1}},
            {"agent_id": "dataset-1", "params": {"limit": 30}},
            {"agent_id": "quality-1", "params": {"min_quality": 0.7}},
        ],
        "description": "Daily research pipeline — crawl, extract, govern, score",
    }
    orch.create_pipeline(**daily_research)

    training_cycle = {
        "name": "training-cycle",
        "steps": [
            {"agent_id": "planner-1", "params": {}},
            {"agent_id": "trainer-1", "params": {"approved": True}},
            {"agent_id": "bench-1", "params": {"tasks": ["HumanEval", "MBPP"], "is_regression_check": True}},
            {"agent_id": "deploy-1", "params": {}},
        ],
        "description": "End-to-end training cycle — plan, train, benchmark, deploy",
    }
    orch.create_pipeline(**training_cycle)

    full_pipeline = {
        "name": "full-auto",
        "steps": [
            {"agent_id": "research-1", "params": {"since_days": 7}},
            {"agent_id": "doc-1", "params": {"since_days": 1}},
            {"agent_id": "dataset-1", "params": {"limit": 100}},
            {"agent_id": "quality-1", "params": {"min_quality": 0.7}},
            {"agent_id": "planner-1", "params": {}},
        ],
        "description": "Full automatic pipeline — research through planning",
    }
    orch.create_pipeline(**full_pipeline)

    return {"created": 3, "pipelines": ["daily-research", "training-cycle", "full-auto"]}


@router.get("/status")
def orchestrator_status():
    orch = get_orchestrator()
    agents = orch.list_agents()
    pipelines = orch.db.fetchall("SELECT name FROM pipeline_definitions WHERE active = 1")
    recent = orch.db.fetchall("SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT 10")
    for r in recent:
        r["result"] = eval(r.get("result", "{}"))
    return {
        "agents": agents,
        "active_pipelines": [p["name"] for p in pipelines],
        "recent_runs": recent,
        "queue_depth": 0,
    }
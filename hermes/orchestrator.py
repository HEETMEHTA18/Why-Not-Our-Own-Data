import asyncio
import uuid
import structlog
import httpx
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

from governor.agents.models import AgentStatus, AgentType, AgentConfig, PipelineDefinition
from governor.agents.base import AgentOrchestrator, BaseAgent
from governor.agents.research_agent import ResearchAgent
from governor.agents.documentation_agent import DocumentationAgent
from governor.agents.dataset_agent import DatasetAgent
from governor.agents.quality_agent import QualityAgent
from governor.agents.training_planner_agent import TrainingPlannerAgent
from governor.agents.training_agent import TrainingAgent
from governor.agents.benchmark_agent import BenchmarkAgent
from governor.agents.deployment_agent import DeploymentAgent
from governor.database.sqlite import SQLiteStore
from governor.eventbus.bus import get_bus, EventBus
from governor.eventbus.models import Event, EventType, EventPriority
from governor.scheduler import PipelineScheduler
from .config import settings

logger = structlog.get_logger()


class HermesOrchestrator:
    def __init__(self):
        self.db = SQLiteStore()
        self.bus: EventBus = get_bus()
        self.orchestrator = AgentOrchestrator(self.db)
        self.scheduler: Optional[PipelineScheduler] = None
        self._initialized = False
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, AgentConfig] = {}

    def register_default_agents(self):
        configs = [
            AgentConfig(agent_id="research-1", agent_type=AgentType.RESEARCH,
                name="Research Agent", description="Reads papers, releases, changelogs from arxiv/GitHub",
                interval_minutes=1440, config={"sources": ["arxiv", "github", "changelogs"]}),
            AgentConfig(agent_id="doc-1", agent_type=AgentType.DOCUMENTATION,
                name="Documentation Agent", description="Monitors API docs, changelogs, deprecation notices",
                interval_minutes=60, config={"watch": ["fastapi", "react", "docker"]}),
            AgentConfig(agent_id="dataset-1", agent_type=AgentType.DATASET,
                name="Dataset Agent", description="Builds structured datasets from extracted knowledge",
                interval_minutes=30),
            AgentConfig(agent_id="quality-1", agent_type=AgentType.QUALITY,
                name="Quality Agent", description="Scores dataset quality across 8 dimensions",
                interval_minutes=30, config={"min_quality_score": 0.6}),
            AgentConfig(agent_id="planner-1", agent_type=AgentType.TRAINING_PLANNER,
                name="Training Planner", description="Decides when training is needed via governance",
                interval_minutes=60),
            AgentConfig(agent_id="trainer-1", agent_type=AgentType.TRAINING,
                name="Training Agent", description="Executes LoRA fine-tuning pipeline",
                interval_minutes=0, config={"model": "llama3.1-8b"}),
            AgentConfig(agent_id="bench-1", agent_type=AgentType.BENCHMARK,
                name="Benchmark Agent", description="Runs benchmarks and regression detection",
                interval_minutes=0),
            AgentConfig(agent_id="deploy-1", agent_type=AgentType.DEPLOYMENT,
                name="Deployment Agent", description="Benchmark-gated deploy with auto-rollback",
                interval_minutes=0),
        ]
        self._agent_configs = {c.agent_id: c for c in configs}
        constructors = {
            AgentType.RESEARCH: ResearchAgent,
            AgentType.DOCUMENTATION: DocumentationAgent,
            AgentType.DATASET: DatasetAgent,
            AgentType.QUALITY: QualityAgent,
            AgentType.TRAINING_PLANNER: TrainingPlannerAgent,
            AgentType.TRAINING: TrainingAgent,
            AgentType.BENCHMARK: BenchmarkAgent,
            AgentType.DEPLOYMENT: DeploymentAgent,
        }
        for c in configs:
            cls = constructors.get(c.agent_type)
            if cls:
                try:
                    agent = cls(c, self.db)
                    self.orchestrator.register_agent(agent)
                    self._agents[c.agent_id] = agent
                    logger.info("hermes_agent_registered", agent=c.name, id=c.agent_id)
                except Exception as e:
                    logger.error("hermes_agent_register_failed", agent=c.name, error=str(e))
            else:
                logger.warning("hermes_no_constructor", agent_type=c.agent_type.value)

    def register_default_pipelines(self):
        pipelines = [
            PipelineDefinition(
                name="daily-research",
                description="Daily research gathering pipeline",
                steps=[
                    {"agent_id": "research-1", "order": 0},
                    {"agent_id": "doc-1", "order": 1},
                    {"agent_id": "dataset-1", "order": 2},
                    {"agent_id": "quality-1", "order": 3},
                ],
            ),
            PipelineDefinition(
                name="training-cycle",
                description="Full training cycle from research to deploy",
                steps=[
                    {"agent_id": "planner-1", "order": 0},
                    {"agent_id": "trainer-1", "order": 1},
                    {"agent_id": "bench-1", "order": 2},
                    {"agent_id": "deploy-1", "order": 3},
                ],
            ),
            PipelineDefinition(
                name="full-auto",
                description="End-to-end autonomous pipeline",
                steps=[
                    {"agent_id": "research-1", "order": 0},
                    {"agent_id": "doc-1", "order": 1},
                    {"agent_id": "dataset-1", "order": 2},
                    {"agent_id": "quality-1", "order": 3},
                    {"agent_id": "planner-1", "order": 4},
                    {"agent_id": "trainer-1", "order": 5},
                    {"agent_id": "bench-1", "order": 6},
                    {"agent_id": "deploy-1", "order": 7},
                ],
            ),
        ]
        for p in pipelines:
            try:
                self.orchestrator.create_pipeline(p.name, p.steps, p.description)
                logger.info("hermes_pipeline_created", name=p.name)
            except Exception as e:
                logger.error("hermes_pipeline_create_failed", name=p.name, error=str(e))

    def init_scheduler(self):
        try:
            self.scheduler = PipelineScheduler(self.db)
            self.scheduler.register_default_jobs(self.orchestrator)
            logger.info("hermes_scheduler_initialized")
        except Exception as e:
            logger.error("hermes_scheduler_init_failed", error=str(e))

    async def initialize(self):
        if self._initialized:
            return
        if not self.bus._running:
            self.bus.start()
        self.register_default_agents()
        self.register_default_pipelines()
        if settings.auto_init_scheduler_jobs:
            self.init_scheduler()
        self._initialized = True
        logger.info("hermes_initialized", agents=len(self._agents))

    def get_status(self) -> dict:
        agents_status = []
        for aid, agent in self._agents.items():
            cfg = self._agent_configs.get(aid)
            agents_status.append({
                "id": aid,
                "name": cfg.name if cfg else aid,
                "type": cfg.agent_type.value if cfg else "unknown",
                "status": agent.status.value,
                "enabled": cfg.enabled if cfg else True,
            })
        return {
            "status": "ready" if self._initialized else "initializing",
            "agents": agents_status,
            "pipelines": list(self.orchestrator._pipelines.keys()),
            "event_bus": self.bus.get_stats().model_dump(),
            "scheduler_running": self.scheduler is not None,
        }

    async def run_agent(self, agent_id: str, context: dict = None) -> dict:
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        run = await agent.run(context=context, triggered_by="hermes:api")
        return {
            "run_id": run.run_id,
            "agent_id": agent_id,
            "status": run.status.value,
            "result": run.result,
            "error": run.error,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

    async def run_pipeline(self, pipeline_name: str, context: dict = None) -> dict:
        results = await self.orchestrator.run_pipeline(pipeline_name, context)
        return {"pipeline": pipeline_name, "steps": results}

    def get_recent_runs(self, agent_id: Optional[str] = None, limit: int = 20) -> List[dict]:
        if agent_id:
            agent = self._agents.get(agent_id)
            if agent:
                return agent.get_recent_runs(limit)
            return []
        rows = self.db.fetchall(
            "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        for r in rows:
            try:
                r["result"] = eval(r.get("result", "{}"))
            except Exception:
                r["result"] = {}
        return rows


_hermes_instance: Optional[HermesOrchestrator] = None


def get_hermes() -> HermesOrchestrator:
    global _hermes_instance
    if _hermes_instance is None:
        _hermes_instance = HermesOrchestrator()
    return _hermes_instance
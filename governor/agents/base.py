import uuid
import asyncio
import time
import structlog
from datetime import datetime, timezone
from typing import Optional, Any, Callable, Coroutine, Dict, List
from abc import ABC, abstractmethod

from .models import AgentStatus, AgentType, AgentConfig, AgentRun
from ..database.sqlite import SQLiteStore
from ..eventbus.bus import get_bus, EventBus
from ..eventbus.models import Event, EventType, EventPriority

logger = structlog.get_logger()


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        self.config = config
        self.db = db or SQLiteStore()
        self.bus = get_bus()
        self._status = AgentStatus.IDLE
        self._current_run: Optional[AgentRun] = None
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT DEFAULT '{}',
                error TEXT,
                triggered_by TEXT DEFAULT 'scheduler'
            )
        """)

    @abstractmethod
    async def execute(self, context: dict = None) -> dict:
        pass

    async def run(self, context: dict = None, triggered_by: str = "manual") -> AgentRun:
        run_id = str(uuid.uuid4())
        self._current_run = AgentRun(
            run_id=run_id,
            agent_id=self.config.agent_id,
            status=AgentStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
            triggered_by=triggered_by,
        )
        self._status = AgentStatus.RUNNING

        logger.info("agent_started", agent=self.config.name, run_id=run_id)

        try:
            result = await self.execute(context or {})
            self._current_run.status = AgentStatus.COMPLETED
            self._current_run.completed_at = datetime.now(timezone.utc).isoformat()
            self._current_run.result = result if isinstance(result, dict) else {"output": str(result)}
            await self.bus.publish_sync(
                EventType.AGENT_COMPLETED,
                self.config.agent_id,
                payload={"run_id": run_id, "agent_type": self.config.agent_type.value, "result_summary": str(result)[:200]},
            )
            logger.info("agent_completed", agent=self.config.name, run_id=run_id)
        except Exception as e:
            self._current_run.status = AgentStatus.FAILED
            self._current_run.completed_at = datetime.now(timezone.utc).isoformat()
            self._current_run.error = str(e)
            await self.bus.publish_sync(
                EventType.ERROR_OCCURRED,
                self.config.agent_id,
                payload={"run_id": run_id, "error": str(e)},
                priority=EventPriority.HIGH,
            ) 
            logger.error("agent_failed", agent=self.config.name, error=str(e))

        self._status = AgentStatus.IDLE
        self._persist_run()
        return self._current_run

    def _persist_run(self):
        if not self._current_run:
            return
        self.db.execute(
            """INSERT OR REPLACE INTO agent_runs
               (id, agent_id, status, started_at, completed_at, result, error, triggered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (self._current_run.run_id, self.config.agent_id, self._current_run.status.value,
             self._current_run.started_at, self._current_run.completed_at or "",
             str(self._current_run.result), self._current_run.error or "",
             self._current_run.triggered_by),
        )

    def get_recent_runs(self, limit: int = 10) -> List[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM agent_runs WHERE agent_id = ? ORDER BY started_at DESC LIMIT ?",
            (self.config.agent_id, limit),
        )
        result = []
        for r in rows:
            r["result"] = eval(r.get("result", "{}"))
            r["status"] = AgentStatus(r["status"])
            result.append(r)
        return result

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def id(self) -> str:
        return self.config.agent_id


class AgentOrchestrator:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.bus = get_bus()
        self._agents: Dict[str, BaseAgent] = {}
        self._pipelines: Dict[str, List[Dict]] = {}
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS agent_registry (
                agent_id TEXT PRIMARY KEY,
                agent_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                config TEXT DEFAULT '{}'
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_definitions (
                name TEXT PRIMARY KEY,
                description TEXT DEFAULT '',
                steps TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1
            )
        """)

    def register_agent(self, agent: BaseAgent) -> str:
        self._agents[agent.id] = agent
        self.db.execute(
            """INSERT OR REPLACE INTO agent_registry
               (agent_id, agent_type, name, description, enabled, config)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (agent.id, agent.config.agent_type.value, agent.config.name,
             agent.config.description, int(agent.config.enabled), str(agent.config.config)),
        )
        logger.info("agent_registered", agent=agent.config.name, id=agent.id)
        return agent.id

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[dict]:
        rows = self.db.fetchall("SELECT * FROM agent_registry")
        for r in rows:
            r["config"] = eval(r.get("config", "{}"))
            r["enabled"] = bool(r["enabled"])
            agent = self._agents.get(r["agent_id"])
            r["status"] = agent.status.value if agent else "unknown"
        return rows

    def create_pipeline(self, name: str, steps: List[Dict], description: str = "") -> str:
        pipeline = {"name": name, "steps": steps, "description": description}
        self._pipelines[name] = steps
        self.db.execute(
            """INSERT OR REPLACE INTO pipeline_definitions
               (name, description, steps, active) VALUES (?, ?, ?, 1)""",
            (name, description, str(steps)),
        )
        logger.info("pipeline_created", name=name, steps=len(steps))
        return name

    async def run_pipeline(self, pipeline_name: str, context: dict = None) -> List[dict]:
        if pipeline_name in self._pipelines:
            steps = self._pipelines[pipeline_name]
        else:
            row = self.db.fetchone(
                "SELECT steps FROM pipeline_definitions WHERE name = ?", (pipeline_name,)
            )
            if not row:
                raise ValueError(f"Pipeline not found: {pipeline_name}")
            steps = eval(row["steps"])
            self._pipelines[pipeline_name] = steps

        results = []
        ctx = context or {}
        for i, step in enumerate(steps):
            agent_id = step.get("agent_id")
            agent = self._agents.get(agent_id)
            if not agent:
                logger.warning("pipeline_step_skipped", step=i, agent_id=agent_id)
                results.append({"step": i, "status": "skipped", "reason": f"agent {agent_id} not found"})
                continue

            logger.info("pipeline_step", pipeline=pipeline_name, step=i, agent=agent.config.name)
            run = await agent.run(context=ctx, triggered_by=f"pipeline:{pipeline_name}")
            ctx[f"run_{agent_id}"] = run.result
            results.append({
                "step": i,
                "agent": agent.config.name,
                "run_id": run.run_id,
                "status": run.status.value,
                "result_summary": str(run.result)[:200] if run.result else "",
            })

            if run.status == AgentStatus.FAILED:
                logger.error("pipeline_failed", pipeline=pipeline_name, step=i, agent=agent.config.name)
                break

        await self.bus.publish_sync(
            EventType.PIPELINE_COMPLETED,
            "orchestrator",
            payload={"pipeline": pipeline_name, "steps_completed": len(results), "results": results},
        )
        return results

    async def run_all_agents(self) -> List[AgentRun]:
        results = []
        for agent_id, agent in self._agents.items():
            if agent.config.enabled:
                run = await agent.run(triggered_by="orchestrator:run_all")
                results.append(run)
        return results
from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum
from datetime import datetime


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    PAUSED = "paused"


class AgentType(str, Enum):
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    EXTRACTOR = "extractor"
    GOVERNOR = "governor"
    DATASET = "dataset"
    QUALITY = "quality"
    TRAINING_PLANNER = "training_planner"
    TRAINING = "training"
    BENCHMARK = "benchmark"
    DEPLOYMENT = "deployment"
    SCHEDULER = "scheduler"


class AgentConfig(BaseModel):
    agent_id: str
    agent_type: AgentType
    name: str
    description: str = ""
    enabled: bool = True
    interval_minutes: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    config: dict = {}


class AgentRun(BaseModel):
    run_id: str
    agent_id: str
    status: AgentStatus
    started_at: str = ""
    completed_at: Optional[str] = None
    result: dict = {}
    error: Optional[str] = None
    triggered_by: str = ""


class PipelineDefinition(BaseModel):
    name: str
    description: str = ""
    steps: List[dict]
    active: bool = True
    schedule_cron: Optional[str] = None


class OrchestratorStatus(BaseModel):
    agents: List[dict]
    active_pipelines: List[str]
    recent_runs: List[dict]
    queue_depth: int
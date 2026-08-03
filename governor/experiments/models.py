from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class ExperimentStatus(str, Enum):
    DESIGNED = "designed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentConfig(BaseModel):
    id: str
    name: str
    description: str
    hypothesis: str
    methodology: str
    metrics: List[str]
    parameters: dict = {}
    created_at: str


class ExperimentRun(BaseModel):
    id: str
    experiment_id: str
    run_number: int
    status: ExperimentStatus
    parameters: dict = {}
    results: dict = {}
    metrics: dict = {}
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


class ExperimentReport(BaseModel):
    id: str
    experiment_id: str
    summary: str
    findings: str
    conclusion: str
    recommendations: List[str] = []
    created_at: str

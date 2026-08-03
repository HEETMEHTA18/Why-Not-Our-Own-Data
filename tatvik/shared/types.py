from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class JobType(str, Enum):
    TRAINING = "training"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    ROLLBACK = "rollback"
    BENCHMARK = "benchmark"


class GPUInfo(BaseModel):
    index: int
    name: str
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_pct: float
    temperature_c: float | None = None


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class ExperimentSummary(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    experiment_type: str
    base_model: str
    adapter_id: str | None = None
    status: Status
    metrics: dict[str, float] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from shared.types import Status


class BaseModelRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    tag: str = "latest"
    digest: str = ""
    size_bytes: int = 0
    is_available: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AdapterRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    base_model_id: str
    version: int = 1
    name: str = ""
    path: str = ""
    dataset_id: str = ""
    dataset_hash: str = ""
    training_config: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    status: Status = Status.PENDING
    parent_adapter_id: str | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    deployed_at: datetime | None = None


class BenchmarkResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    adapter_id: str | None = None
    base_model_id: str
    task: str
    score: float
    metrics: dict[str, Any] = Field(default_factory=dict)
    samples: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ExperimentRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    experiment_type: str
    base_model_id: str
    adapter_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    status: Status = Status.PENDING
    metrics: dict[str, Any] = Field(default_factory=dict)
    benchmark_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ModelVersion(BaseModel):
    version: int
    adapter_id: str
    adapter_name: str
    base_model: str
    status: str
    metrics: dict[str, float] = Field(default_factory=dict)
    benchmark_scores: dict[str, float] = Field(default_factory=dict)
    dataset_hash: str = ""
    created_at: datetime
    deployed_at: datetime | None = None
    notes: str = ""

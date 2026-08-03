from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from shared.config import settings
from shared.types import Status

from .models import (
    AdapterRecord,
    BaseModelRecord,
    BenchmarkResult,
    ExperimentRecord,
    ModelVersion,
)
from .repository import RegistryRepository

logger = structlog.get_logger()


class RegistryManager:
    def __init__(self, repository: RegistryRepository) -> None:
        self._repo = repository

    async def register_base_model(
        self, name: str, tag: str = "latest", digest: str = "", size_bytes: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> BaseModelRecord:
        record = BaseModelRecord(
            name=name, tag=tag, digest=digest, size_bytes=size_bytes,
            metadata=metadata or {},
        )
        return await self._repo.save_base_model(record)

    async def create_adapter(
        self, base_model_id: str, dataset_id: str = "", dataset_hash: str = "",
        training_config: dict[str, Any] | None = None, parent_adapter_id: str | None = None,
        notes: str = "",
    ) -> AdapterRecord:
        adapters = await self._repo.list_adapters(base_model_id)
        next_version = (adapters[0].version + 1) if adapters else 1

        record = AdapterRecord(
            base_model_id=base_model_id,
            version=next_version,
            name=f"v{next_version}",
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            training_config=training_config or {},
            parent_adapter_id=parent_adapter_id,
            notes=notes,
            status=Status.PENDING,
        )
        return await self._repo.save_adapter(record)

    async def update_adapter_status(
        self, adapter_id: str, status: Status, metrics: dict[str, float] | None = None,
    ) -> AdapterRecord | None:
        adapter = await self._repo.get_adapter(adapter_id)
        if not adapter:
            logger.error("adapter_not_found", adapter_id=adapter_id)
            return None
        adapter.status = status
        if metrics:
            adapter.metrics.update(metrics)
        if status == Status.COMPLETED:
            adapter.deployed_at = datetime.now()
        return await self._repo.save_adapter(adapter)

    async def update_adapter_path(self, adapter_id: str, path: str) -> AdapterRecord | None:
        adapter = await self._repo.get_adapter(adapter_id)
        if not adapter:
            return None
        adapter.path = path
        return await self._repo.save_adapter(adapter)

    async def record_benchmark(
        self, adapter_id: str | None, base_model_id: str, task: str, score: float,
        metrics: dict[str, float] | None = None, samples: int = 0,
        config: dict[str, Any] | None = None,
    ) -> BenchmarkResult:
        record = BenchmarkResult(
            adapter_id=adapter_id,
            base_model_id=base_model_id,
            task=task,
            score=score,
            metrics=metrics or {},
            samples=samples,
            config=config or {},
        )
        return await self._repo.save_benchmark(record)

    async def create_experiment(
        self, experiment_type: str, base_model_id: str, adapter_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> ExperimentRecord:
        record = ExperimentRecord(
            experiment_type=experiment_type,
            base_model_id=base_model_id,
            adapter_id=adapter_id,
            config=config or {},
        )
        return await self._repo.save_experiment(record)

    async def update_experiment(
        self, experiment_id: str, status: Status, metrics: dict[str, float] | None = None,
        error: str | None = None,
    ) -> ExperimentRecord | None:
        exps = await self._repo.list_experiments(limit=1000)
        exp = next((e for e in exps if e.id == experiment_id), None)
        if not exp:
            return None
        exp.status = status
        if metrics:
            exp.metrics.update(metrics)
        if error:
            exp.error = error
        if status == Status.RUNNING:
            exp.started_at = datetime.now()
        if status in (Status.COMPLETED, Status.FAILED):
            exp.completed_at = datetime.now()
        return await self._repo.save_experiment(exp)

    async def get_versions(self, base_model_id: str) -> list[ModelVersion]:
        adapters = await self._repo.list_adapters(base_model_id)
        benchmarks = await self._repo.get_benchmarks()
        bench_by_adapter: dict[str, dict[str, float]] = {}
        for b in benchmarks:
            if b.adapter_id:
                bench_by_adapter.setdefault(b.adapter_id, {})[b.task] = b.score

        versions = []
        for a in adapters:
            versions.append(ModelVersion(
                version=a.version,
                adapter_id=a.id,
                adapter_name=a.name,
                base_model=base_model_id,
                status=a.status.value,
                metrics=a.metrics,
                benchmark_scores=bench_by_adapter.get(a.id, {}),
                dataset_hash=a.dataset_hash,
                created_at=a.created_at,
                deployed_at=a.deployed_at,
                notes=a.notes,
            ))
        return versions

    async def get_base_models(self) -> list[BaseModelRecord]:
        return await self._repo.list_base_models()

    async def get_adapters(self, base_model_id: str | None = None) -> list[AdapterRecord]:
        return await self._repo.list_adapters(base_model_id)

    async def get_benchmarks(self, adapter_id: str | None = None) -> list[BenchmarkResult]:
        return await self._repo.get_benchmarks(adapter_id)

    async def get_experiments(self, limit: int = 50) -> list[ExperimentRecord]:
        return await self._repo.list_experiments(limit)

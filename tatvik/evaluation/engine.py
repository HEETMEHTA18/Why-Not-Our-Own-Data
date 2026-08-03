from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator
from uuid import uuid4

import structlog

from registry.manager import RegistryManager
from registry.models import BenchmarkResult
from shared.config import settings
from shared.types import Status

from .models import BenchmarkConfig, BenchmarkTask
from .runner import BenchmarkRunner

logger = structlog.get_logger()


class BenchmarkEngine:
    def __init__(self, registry: RegistryManager, runner: BenchmarkRunner | None = None) -> None:
        self._registry = registry
        self._runner = runner or BenchmarkRunner()

    async def evaluate(
        self,
        base_model: str,
        adapter_path: str | None = None,
        config: BenchmarkConfig | None = None,
        experiment_id: str | None = None,
    ) -> list[BenchmarkResult]:
        cfg = config or BenchmarkConfig()
        results: list[BenchmarkResult] = []

        model_id = base_model.replace(":", "-").replace("/", "-")
        base_record = (await self._registry.get_base_models())
        base_db = next((b for b in base_record if b.name == base_model), None)
        base_model_id = base_db.id if base_db else model_id

        for task in cfg.tasks:
            logger.info("benchmark_start", task=task.value, model=base_model)
            try:
                score, metrics, samples = await self._runner.run_task(
                    task=task, model_name=base_model,
                    adapter_path=adapter_path, config=cfg,
                )
                result = await self._registry.record_benchmark(
                    adapter_id=None,
                    base_model_id=base_model_id,
                    task=task.value,
                    score=score,
                    metrics=metrics,
                    samples=samples,
                    config={"model": base_model, "adapter": adapter_path, **cfg.model_dump()},
                )
                results.append(result)
                logger.info("benchmark_complete", task=task.value, score=score)
            except Exception as e:
                logger.error("benchmark_failed", task=task.value, error=str(e))
                raise

        return results

    async def compare(
        self,
        base_model: str,
        adapter_ids: list[str],
        config: BenchmarkConfig | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        cfg = config or BenchmarkConfig()
        comparison: dict[str, list[dict[str, Any]]] = {}

        for task in cfg.tasks:
            task_results: list[dict[str, Any]] = []
            base_scores = await self._registry.get_benchmarks()
            base_for_task = [b for b in base_scores if b.task == task.value and b.adapter_id is None]
            if base_for_task:
                task_results.append({
                    "name": "base",
                    "adapter_id": None,
                    "score": base_for_task[0].score,
                    "metrics": base_for_task[0].metrics,
                })

            for aid in adapter_ids:
                adapter_benchmarks = await self._registry.get_benchmarks(adapter_id=aid)
                for b in adapter_benchmarks:
                    if b.task == task.value:
                        adapter = await self._registry.get_adapters()
                        a = next((a for a in adapter if a.id == aid), None)
                        task_results.append({
                            "name": a.name if a else aid[:8],
                            "adapter_id": aid,
                            "score": b.score,
                            "metrics": b.metrics,
                        })

            task_results.sort(key=lambda x: x["score"], reverse=True)
            comparison[task.value] = task_results

        return comparison

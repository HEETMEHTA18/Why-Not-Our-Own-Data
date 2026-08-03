from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from evaluation.engine import BenchmarkEngine
from registry.manager import RegistryManager
from registry.models import AdapterRecord, BenchmarkResult, ExperimentRecord
from shared.config import settings
from shared.types import Status

logger = structlog.get_logger()


class RollbackManager:
    def __init__(self, registry: RegistryManager, benchmark_engine: BenchmarkEngine) -> None:
        self._registry = registry
        self._benchmark_engine = benchmark_engine

    async def should_rollback(self, adapter_id: str, benchmark_results: list[BenchmarkResult]) -> bool:
        adapter = await self._get_adapter(adapter_id)
        if not adapter:
            return False

        base_model_id = adapter.base_model_id
        previous_adapter = await self._get_previous_deployed(base_model_id, adapter.version)
        if not previous_adapter:
            logger.info("no_previous_adapter_to_compare", adapter_id=adapter_id)
            return False

        previous_benchmarks = await self._registry.get_benchmarks(adapter_id=previous_adapter.id)
        if not previous_benchmarks:
            logger.info("no_previous_benchmarks_to_compare", adapter_id=adapter_id)
            return False

        previous_scores = {b.task: b.score for b in previous_benchmarks}
        current_scores = {b.task: b.score for b in benchmark_results if b.adapter_id == adapter_id}

        regression_count = 0
        total_tasks = 0
        regression_details = []

        for task, prev_score in previous_scores.items():
            curr_score = current_scores.get(task)
            if curr_score is not None:
                total_tasks += 1
                delta = curr_score - prev_score
                if delta < settings.benchmark_reject_threshold:
                    regression_count += 1
                    regression_details.append({
                        "task": task,
                        "previous": prev_score,
                        "current": curr_score,
                        "delta": delta,
                    })

        if total_tasks == 0:
            return False

        regression_rate = regression_count / total_tasks
        avg_delta = sum(d["delta"] for d in regression_details) / total_tasks if regression_details else 0

        should_rollback = regression_rate > 0.3 or avg_delta < -0.05

        if should_rollback:
            logger.warning(
                "rollback_recommended",
                adapter_id=adapter_id,
                regression_rate=regression_rate,
                avg_delta=avg_delta,
                details=regression_details,
            )
        else:
            logger.info(
                "rollback_not_needed",
                adapter_id=adapter_id,
                regression_rate=regression_rate,
                avg_delta=avg_delta,
            )

        return should_rollback

    async def execute_rollback(
        self, adapter_id: str, reason: str = "",
    ) -> dict[str, Any]:
        adapter = await self._get_adapter(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")

        await self._registry.update_adapter_status(adapter_id, Status.ROLLED_BACK, metrics={"rollback_reason": reason})

        base_model_id = adapter.base_model_id
        previous = await self._get_previous_deployed(base_model_id, adapter.version)
        rollback_target = previous.id if previous else None
        rollback_version = previous.version if previous else 0

        logger.info(
            "rollback_executed",
            adapter_id=adapter_id,
            reason=reason,
            rolled_back_to=rollback_target,
        )

        return {
            "adapter_id": adapter_id,
            "version": adapter.version,
            "status": "rolled_back",
            "reason": reason,
            "rolled_back_to_adapter": rollback_target,
            "rolled_back_to_version": rollback_version,
        }

    async def _get_adapter(self, adapter_id: str) -> AdapterRecord | None:
        adapters = await self._registry.get_adapters()
        return next((a for a in adapters if a.id == adapter_id), None)

    async def _get_previous_deployed(self, base_model_id: str, current_version: int) -> AdapterRecord | None:
        adapters = await self._registry.get_adapters(base_model_id)
        deployed = [a for a in adapters if a.deployed_at and a.version < current_version]
        if not deployed:
            return None
        return max(deployed, key=lambda a: a.deployed_at or datetime.min)

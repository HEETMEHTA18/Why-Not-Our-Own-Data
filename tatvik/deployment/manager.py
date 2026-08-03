from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from evaluation.engine import BenchmarkEngine
from registry.manager import RegistryManager
from registry.models import AdapterRecord, BenchmarkResult, ModelVersion
from shared.config import settings
from shared.types import Status

logger = structlog.get_logger()


class DeploymentManager:
    def __init__(self, registry: RegistryManager, benchmark_engine: BenchmarkEngine) -> None:
        self._registry = registry
        self._benchmark_engine = benchmark_engine

    async def deploy(self, adapter_id: str) -> dict[str, Any]:
        adapter = await self._registry.get_adapters()
        target = next((a for a in adapter if a.id == adapter_id), None)
        if not target:
            raise ValueError(f"Adapter not found: {adapter_id}")
        if target.status != Status.COMPLETED:
            raise ValueError(f"Adapter {adapter_id} has status {target.status.value}, expected completed")

        base = await self._registry.get_base_models()
        base_model = next((b for b in base if b.id == target.base_model_id), None)
        base_name = base_model.name if base_model else target.base_model_id

        existing_adapters = await self._registry.get_adapters(target.base_model_id)
        deployed = [a for a in existing_adapters if a.status == Status.COMPLETED and a.deployed_at]

        if deployed:
            latest = max(deployed, key=lambda a: a.deployed_at or datetime.min)
            logger.info("previous_deployment_found", adapter_id=latest.id, version=latest.version)

        await self._registry.update_adapter_status(target.id, Status.COMPLETED)
        target.deployed_at = datetime.now()
        await self._registry._repo.save_adapter(target)

        logger.info("adapter_deployed", adapter_id=adapter_id, version=target.version)

        return {
            "adapter_id": adapter_id,
            "version": target.version,
            "base_model": base_name,
            "deployed_at": target.deployed_at.isoformat() if target.deployed_at else "",
            "status": "deployed",
        }

    async def compare_versions(self, base_model_id: str) -> list[dict[str, Any]]:
        versions = await self._registry.get_versions(base_model_id)
        return [
            {
                "version": v.version,
                "adapter_id": v.adapter_id,
                "status": v.status,
                "metrics": v.metrics,
                "benchmarks": v.benchmark_scores,
                "created_at": v.created_at.isoformat(),
                "deployed_at": v.deployed_at.isoformat() if v.deployed_at else None,
            }
            for v in versions
        ]

    async def get_deployment_status(self, base_model_id: str) -> dict[str, Any]:
        versions = await self._registry.get_versions(base_model_id)
        deployed = [v for v in versions if v.deployed_at]
        current = max(deployed, key=lambda v: v.deployed_at or datetime.min) if deployed else None

        return {
            "base_model_id": base_model_id,
            "total_versions": len(versions),
            "current_version": current.version if current else None,
            "current_adapter_id": current.adapter_id if current else None,
            "deployed_versions": [v.version for v in deployed],
            "pending_versions": [v.version for v in versions if v.status == Status.PENDING.value],
            "failed_versions": [v.version for v in versions if v.status == Status.FAILED.value],
        }

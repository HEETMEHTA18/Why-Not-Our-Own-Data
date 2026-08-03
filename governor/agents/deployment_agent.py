from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from .base import BaseAgent
from .models import AgentConfig

import structlog
logger = structlog.get_logger()


class DeploymentAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        adapter_id = ctx.get("adapter_id")
        adapter_version = ctx.get("adapter_version", "unknown")
        benchmark_results = ctx.get("benchmark_results", [])

        if not benchmark_results:
            return {"status": "failed", "reason": "no_benchmark_results"}

        regressed = any(
            r.get("regression", {}).get("regressed", False)
            for r in benchmark_results
            if isinstance(r, dict)
        )
        passed = all(
            r.get("score", 0) >= 0.5 for r in benchmark_results if isinstance(r, dict)
        )

        if regressed or not passed:
            await get_bus().publish_sync(
                EventType.ROLLBACK_EXECUTED, "deployment_agent",
                payload={
                    "adapter_id": adapter_id,
                    "version": adapter_version,
                    "reason": "regression" if regressed else "below_threshold",
                },
                priority=EventPriority.CRITICAL,
            )
            logger.warning("deployment_blocked", adapter=adapter_id, regressed=regressed, passed=passed)
            return {
                "status": "rollback",
                "adapter_id": adapter_id,
                "reason": "Benchmark regression detected" if regressed else "Benchmark below threshold",
                "rolled_back_to": f"v{int(adapter_version) - 1}" if adapter_version != "unknown" else "base",
            }

        await get_bus().publish_sync(
            EventType.DEPLOYMENT_COMPLETED, "deployment_agent",
            payload={"adapter_id": adapter_id, "version": adapter_version},
            priority=EventPriority.HIGH,
        )

        logger.info("adapter_deployed", adapter=adapter_id, version=adapter_version)
        return {
            "status": "deployed",
            "adapter_id": adapter_id,
            "version": adapter_version,
            "deployed_at": __import__("datetime").datetime.now().isoformat(),
        }
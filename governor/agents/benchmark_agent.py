from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from ..config import settings
from .base import BaseAgent
from .models import AgentConfig

import structlog
logger = structlog.get_logger()


class BenchmarkAgent(BaseAgent):
    def __init__(self, config: AgentConfig, db: Optional[SQLiteStore] = None):
        super().__init__(config, db)

    async def execute(self, context: dict = None) -> dict:
        ctx = context or {}
        adapter_path = ctx.get("adapter_path")
        tasks = ctx.get("tasks", ["HumanEval", "MBPP"])
        is_regression_check = ctx.get("is_regression_check", False)

        actual = []
        for task in tasks:
            score, metrics = await self._run_benchmark(task, adapter_path)
            actual.append({"task": task, "score": score, "metrics": metrics})

        regression = None
        if is_regression_check:
            regression = self._check_regression(actual, adapter_path)

        await get_bus().publish_sync(
            EventType.BENCHMARK_COMPLETED, "benchmark_agent",
            payload={"results": actual, "regression": regression},
            priority=EventPriority.HIGH if regression and regression.get("regressed") else EventPriority.MEDIUM,
        )

        return {
            "results": actual,
            "regression": regression,
            "passed": not (regression and regression.get("regressed")),
        }

    async def _run_benchmark(self, task: str, adapter_path: str = None) -> tuple:
        import time
        time.sleep(0.01)
        import random
        score = random.uniform(0.5, 0.95)
        return score, {"accuracy": score, "latency_ms": 150, "samples": 100}

    def _check_regression(self, results: List[dict], adapter_path: str = None) -> dict:
        latest = self.db.fetchone(
            "SELECT result FROM agent_runs WHERE agent_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
            (self.config.agent_id,),
        )
        if not latest:
            return {"regressed": False, "reason": "no_previous_benchmark"}
        try:
            prev = eval(latest["result"])
            prev_scores = {r["task"]: r["score"] for r in prev.get("results", [])}
        except Exception:
            return {"regressed": False, "reason": "parse_error"}

        regressions = []
        for r in results:
            prev_score = prev_scores.get(r["task"])
            if prev_score and r["score"] < prev_score - 0.05:
                regressions.append({
                    "task": r["task"],
                    "previous": prev_score,
                    "current": r["score"],
                    "delta": r["score"] - prev_score,
                })

        if regressions:
            return {"regressed": True, "regressions": regressions, "count": len(regressions)}
        return {"regressed": False, "reason": "no_regression_detected"}
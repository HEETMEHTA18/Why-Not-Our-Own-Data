from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import Container, get_container
from evaluation.models import BenchmarkConfig, BenchmarkTask
from registry.models import BenchmarkResult
from shared.types import JobType

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.post("/run")
async def run_evaluation(
    base_model: str,
    adapter_path: str | None = None,
    config: BenchmarkConfig | None = None,
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    cfg = config or BenchmarkConfig()

    async def eval_job(model: str, adapter: str | None, conf: BenchmarkConfig) -> list[BenchmarkResult]:
        return await container.benchmark_engine.evaluate(
            base_model=model, adapter_path=adapter, config=conf,
        )

    job_id = await container.job_queue.enqueue(
        __import__("scheduler.queue", fromlist=[""]).Job(
            job_type=JobType.EVALUATION,
            handler=eval_job,
            params={"model": base_model, "adapter": adapter_path, "conf": cfg},
        )
    )
    return {"job_id": job_id, "status": "queued", "base_model": base_model}


@router.get("/benchmarks")
async def list_benchmarks(
    adapter_id: str | None = None,
    container: Container = Depends(get_container),
) -> list[BenchmarkResult]:
    return await container.registry_manager.get_benchmarks(adapter_id)


@router.get("/compare")
async def compare_adapters(
    base_model: str,
    adapter_ids: str,
    container: Container = Depends(get_container),
) -> dict[str, list[dict[str, Any]]]:
    ids = [a.strip() for a in adapter_ids.split(",") if a.strip()]
    return await container.benchmark_engine.compare(base_model, ids)


@router.get("/suites")
async def list_suites(
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    from evaluation.models import STANDARD_SUITES
    return {k: v.model_dump() for k, v in STANDARD_SUITES.items()}

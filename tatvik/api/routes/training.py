from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import Container, get_container
from registry.models import AdapterRecord
from shared.types import JobType, Status
from training.config import TrainingConfig

router = APIRouter(prefix="/training", tags=["Training"])


@router.post("")
async def start_training(
    config: TrainingConfig, container: Container = Depends(get_container),
) -> dict[str, Any]:
    async def train_job(cfg: TrainingConfig) -> AdapterRecord:
        return await container.training_engine.train(cfg)

    job_id = await container.job_queue.enqueue(
        __import__("scheduler.queue", fromlist=[""]).Job(
            job_type=JobType.TRAINING,
            handler=train_job,
            params={"cfg": config},
        )
    )
    return {"job_id": job_id, "status": "queued", "config": config.model_dump()}


@router.get("/status")
async def training_status(container: Container = Depends(get_container)) -> list[dict[str, Any]]:
    jobs = container.job_queue.list_jobs()
    return [
        {
            "id": j.id,
            "type": j.job_type.value,
            "status": j.status.value,
            "progress": j.progress,
            "error": j.error,
            "created_at": j.created_at.isoformat(),
            "started_at": j.started_at.isoformat() if j.started_at else None,
        }
        for j in jobs if j.job_type == JobType.TRAINING
    ]


@router.post("/cancel/{job_id}")
async def cancel_training(job_id: str, container: Container = Depends(get_container)) -> dict[str, str]:
    cancelled = await container.job_queue.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/adapters")
async def list_adapters(
    base_model_id: str | None = None,
    container: Container = Depends(get_container),
) -> list[AdapterRecord]:
    return await container.registry_manager.get_adapters(base_model_id)


@router.get("/adapters/{adapter_id}")
async def get_adapter(
    adapter_id: str, container: Container = Depends(get_container),
) -> AdapterRecord:
    adapters = await container.registry_manager.get_adapters()
    adapter = next((a for a in adapters if a.id == adapter_id), None)
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")
    return adapter

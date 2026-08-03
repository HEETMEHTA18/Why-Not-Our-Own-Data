from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.deps import Container, get_container
from registry.models import ExperimentRecord

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.get("")
async def list_experiments(
    limit: int = 50, container: Container = Depends(get_container),
) -> list[ExperimentRecord]:
    return await container.registry_manager.get_experiments(limit)


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str, container: Container = Depends(get_container),
) -> ExperimentRecord | None:
    experiments = await container.registry_manager.get_experiments(1000)
    return next((e for e in experiments if e.id == experiment_id), None)

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import Container, get_container
from registry.models import BaseModelRecord, ExperimentRecord, ModelVersion
from shared.types import PaginatedResponse

router = APIRouter(prefix="/registry", tags=["Registry"])


@router.get("/models")
async def list_base_models(container: Container = Depends(get_container)) -> list[BaseModelRecord]:
    return await container.registry_manager.get_base_models()


@router.get("/models/{base_model_id}")
async def get_base_model(
    base_model_id: str, container: Container = Depends(get_container),
) -> BaseModelRecord:
    models = await container.registry_manager.get_base_models()
    model = next((m for m in models if m.id == base_model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Base model not found")
    return model


@router.get("/versions/{base_model_id}")
async def list_versions(
    base_model_id: str, container: Container = Depends(get_container),
) -> list[ModelVersion]:
    return await container.registry_manager.get_versions(base_model_id)


@router.get("/experiments")
async def list_experiments(
    limit: int = 50, container: Container = Depends(get_container),
) -> list[ExperimentRecord]:
    return await container.registry_manager.get_experiments(limit)


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str, container: Container = Depends(get_container),
) -> ExperimentRecord:
    experiments = await container.registry_manager.get_experiments(1000)
    exp = next((e for e in experiments if e.id == experiment_id), None)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp

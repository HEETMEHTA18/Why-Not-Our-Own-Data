from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.deps import Container, get_container

router = APIRouter(prefix="/deployment", tags=["Deployment"])


@router.post("/deploy/{adapter_id}")
async def deploy_adapter(
    adapter_id: str, container: Container = Depends(get_container),
) -> dict[str, Any]:
    try:
        return await container.deployment_manager.deploy(adapter_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rollback/{adapter_id}")
async def rollback_adapter(
    adapter_id: str, reason: str = "", container: Container = Depends(get_container),
) -> dict[str, Any]:
    try:
        return await container.rollback_manager.execute_rollback(adapter_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/should-rollback/{adapter_id}")
async def should_rollback(
    adapter_id: str, container: Container = Depends(get_container),
) -> dict[str, Any]:
    benchmarks = await container.registry_manager.get_benchmarks(adapter_id)
    result = await container.rollback_manager.should_rollback(adapter_id, benchmarks)
    return {"adapter_id": adapter_id, "should_rollback": result}


@router.get("/compare/{base_model_id}")
async def compare_versions(
    base_model_id: str, container: Container = Depends(get_container),
) -> list[dict[str, Any]]:
    return await container.deployment_manager.compare_versions(base_model_id)


@router.get("/status/{base_model_id}")
async def deployment_status(
    base_model_id: str, container: Container = Depends(get_container),
) -> dict[str, Any]:
    return await container.deployment_manager.get_deployment_status(base_model_id)

from __future__ import annotations

import pytest

from shared.types import Status


@pytest.mark.asyncio
async def test_deploy_adapter(registry_manager, registered_base_model):
    from deployment.manager import DeploymentManager
    from evaluation.engine import BenchmarkEngine
    from evaluation.runner import BenchmarkRunner

    adapter = await registry_manager.create_adapter(
        base_model_id=registered_base_model.id,
        notes="Test deploy",
    )
    await registry_manager.update_adapter_status(adapter.id, Status.COMPLETED)

    benchmark_engine = BenchmarkEngine(registry_manager)
    dm = DeploymentManager(registry_manager, benchmark_engine)

    result = await dm.deploy(adapter.id)
    assert result["adapter_id"] == adapter.id
    assert result["status"] == "deployed"


@pytest.mark.asyncio
async def test_get_deployment_status(registry_manager, registered_base_model):
    from deployment.manager import DeploymentManager
    from evaluation.engine import BenchmarkEngine

    benchmark_engine = BenchmarkEngine(registry_manager)
    dm = DeploymentManager(registry_manager, benchmark_engine)

    status = await dm.get_deployment_status(registered_base_model.id)
    assert status["base_model_id"] == registered_base_model.id
    assert status["total_versions"] == 0


@pytest.mark.asyncio
async def test_compare_versions(registry_manager, registered_base_model):
    from deployment.manager import DeploymentManager
    from evaluation.engine import BenchmarkEngine

    await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    benchmark_engine = BenchmarkEngine(registry_manager)
    dm = DeploymentManager(registry_manager, benchmark_engine)

    versions = await dm.compare_versions(registered_base_model.id)
    assert len(versions) >= 1

from __future__ import annotations

from datetime import datetime

import pytest

from registry.models import BenchmarkResult
from shared.types import Status


@pytest.mark.asyncio
async def test_should_rollback_no_previous(registry_manager, registered_base_model):
    from deployment.rollback import RollbackManager
    from evaluation.engine import BenchmarkEngine

    adapter = await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    benchmark_engine = BenchmarkEngine(registry_manager)
    rm = RollbackManager(registry_manager, benchmark_engine)

    result = await rm.should_rollback(adapter.id, [])
    assert result is False


@pytest.mark.asyncio
async def test_execute_rollback(registry_manager, registered_base_model):
    from deployment.rollback import RollbackManager
    from evaluation.engine import BenchmarkEngine

    adapter = await registry_manager.create_adapter(base_model_id=registered_base_model.id)

    benchmark_engine = BenchmarkEngine(registry_manager)
    rm = RollbackManager(registry_manager, benchmark_engine)

    result = await rm.execute_rollback(adapter.id, reason="Performance regression")
    assert result["adapter_id"] == adapter.id
    assert result["status"] == "rolled_back"
    assert result["reason"] == "Performance regression"


@pytest.mark.asyncio
async def test_rollback_nonexistent_adapter(registry_manager, registered_base_model):
    from deployment.rollback import RollbackManager
    from evaluation.engine import BenchmarkEngine

    benchmark_engine = BenchmarkEngine(registry_manager)
    rm = RollbackManager(registry_manager, benchmark_engine)

    with pytest.raises(ValueError):
        await rm.execute_rollback("nonexistent-id")

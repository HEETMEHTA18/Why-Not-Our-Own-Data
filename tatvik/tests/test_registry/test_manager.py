from __future__ import annotations

import pytest

from shared.types import Status


@pytest.mark.asyncio
async def test_register_base_model(registry_manager):
    record = await registry_manager.register_base_model(
        name="llama3.1-8b", tag="latest", digest="abc",
    )
    assert record.name == "llama3.1-8b"
    assert record.id is not None


@pytest.mark.asyncio
async def test_create_adapter(registry_manager, registered_base_model):
    adapter = await registry_manager.create_adapter(
        base_model_id=registered_base_model.id,
        dataset_id="ds-1",
        notes="Test adapter",
    )
    assert adapter.base_model_id == registered_base_model.id
    assert adapter.version == 1
    assert adapter.status == Status.PENDING


@pytest.mark.asyncio
async def test_adapter_version_increment(registry_manager, registered_base_model):
    await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    adapter2 = await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    assert adapter2.version == 2


@pytest.mark.asyncio
async def test_update_adapter_status(registry_manager, registered_base_model):
    adapter = await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    updated = await registry_manager.update_adapter_status(
        adapter.id, Status.COMPLETED, {"loss": 0.5},
    )
    assert updated is not None
    assert updated.status == Status.COMPLETED
    assert updated.metrics.get("loss") == 0.5


@pytest.mark.asyncio
async def test_record_benchmark(registry_manager, registered_base_model):
    bm = await registry_manager.record_benchmark(
        adapter_id=None,
        base_model_id=registered_base_model.id,
        task="mmlu",
        score=0.72,
    )
    assert bm.task == "mmlu"
    assert bm.score == 0.72


@pytest.mark.asyncio
async def test_create_experiment(registry_manager, registered_base_model):
    exp = await registry_manager.create_experiment(
        experiment_type="training",
        base_model_id=registered_base_model.id,
    )
    assert exp.experiment_type == "training"
    assert exp.status == Status.PENDING


@pytest.mark.asyncio
async def test_get_versions(registry_manager, registered_base_model):
    await registry_manager.create_adapter(base_model_id=registered_base_model.id)
    versions = await registry_manager.get_versions(registered_base_model.id)
    assert len(versions) == 1
    assert versions[0].version == 1

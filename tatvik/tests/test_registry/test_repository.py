from __future__ import annotations

import pytest

from registry.models import AdapterRecord, BaseModelRecord, BenchmarkResult, ExperimentRecord
from shared.types import Status


@pytest.mark.asyncio
async def test_save_and_get_base_model(registry_repo):
    record = BaseModelRecord(name="llama3.1-8b", tag="latest")
    saved = await registry_repo.save_base_model(record)
    assert saved.id == record.id

    fetched = await registry_repo.get_base_model(record.id)
    assert fetched is not None
    assert fetched.name == "llama3.1-8b"


@pytest.mark.asyncio
async def test_list_base_models(registry_repo):
    await registry_repo.save_base_model(BaseModelRecord(name="model-a"))
    await registry_repo.save_base_model(BaseModelRecord(name="model-b"))
    models = await registry_repo.list_base_models()
    assert len(models) >= 2


@pytest.mark.asyncio
async def test_save_and_get_adapter(registry_repo):
    adapter = AdapterRecord(
        base_model_id="base-1",
        version=1,
        name="v1",
        path="/tmp/adapter",
        status=Status.PENDING,
    )
    saved = await registry_repo.save_adapter(adapter)
    assert saved.id == adapter.id

    fetched = await registry_repo.get_adapter(adapter.id)
    assert fetched is not None
    assert fetched.base_model_id == "base-1"


@pytest.mark.asyncio
async def test_list_adapters(registry_repo):
    await registry_repo.save_adapter(AdapterRecord(base_model_id="base-1", version=1))
    await registry_repo.save_adapter(AdapterRecord(base_model_id="base-1", version=2))
    adapters = await registry_repo.list_adapters("base-1")
    assert len(adapters) == 2


@pytest.mark.asyncio
async def test_get_latest_adapter(registry_repo):
    await registry_repo.save_adapter(AdapterRecord(base_model_id="base-1", version=1))
    await registry_repo.save_adapter(AdapterRecord(base_model_id="base-1", version=2))
    latest = await registry_repo.get_latest_adapter("base-1")
    assert latest is not None
    assert latest.version == 2


@pytest.mark.asyncio
async def test_save_benchmark(registry_repo):
    bm = BenchmarkResult(base_model_id="base-1", task="mmlu", score=0.72)
    saved = await registry_repo.save_benchmark(bm)
    assert saved.id == bm.id


@pytest.mark.asyncio
async def test_save_experiment(registry_repo):
    exp = ExperimentRecord(
        experiment_type="training",
        base_model_id="base-1",
        status=Status.RUNNING,
    )
    saved = await registry_repo.save_experiment(exp)
    assert saved.id == exp.id

    experiments = await registry_repo.list_experiments()
    assert len(experiments) >= 1

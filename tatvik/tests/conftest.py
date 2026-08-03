from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from shared.config import settings
from shared.types import Status


@pytest.fixture(autouse=True)
def test_settings(tmp_path: Path) -> None:
    settings.data_dir = tmp_path / "data"
    settings.adapters_dir = settings.data_dir / "adapters"
    settings.experiments_dir = settings.data_dir / "experiments"
    settings.benchmarks_dir = settings.data_dir / "benchmarks"
    registry_db = settings.data_dir / "registry"
    registry_db.mkdir(parents=True, exist_ok=True)
    settings.registry_db = registry_db / "registry.db"
    settings.registry_db_url = ""
    for d in [settings.data_dir, settings.adapters_dir, settings.experiments_dir, settings.benchmarks_dir]:
        d.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def mock_ollama_client():
    client = AsyncMock()
    client.health = AsyncMock(return_value=True)
    client.list_models = AsyncMock(return_value=[])
    client.generate = AsyncMock()
    client.chat = AsyncMock()
    client.version = AsyncMock(return_value="0.5.0")
    client.close = AsyncMock()
    client.is_running = True
    return client


@pytest_asyncio.fixture
async def registry_repo():
    from registry.repository import RegistryRepository
    repo = RegistryRepository()
    await repo.initialize()
    yield repo
    await repo.close()


@pytest_asyncio.fixture
async def registry_manager(registry_repo):
    from registry.manager import RegistryManager
    return RegistryManager(registry_repo)


@pytest.fixture
def adapter_manager():
    from training.adapter import AdapterManager
    return AdapterManager()


@pytest.fixture
def benchmark_runner():
    from evaluation.runner import BenchmarkRunner
    return BenchmarkRunner()


@pytest.fixture
def job_queue():
    from scheduler.queue import JobQueue
    return JobQueue(max_concurrent=2)


@pytest.fixture
def gpu_monitor():
    from monitor.gpu import GPUMonitor
    return GPUMonitor()


@pytest_asyncio.fixture
async def registered_base_model(registry_manager):
    return await registry_manager.register_base_model(
        name="llama3.1-8b-instruct",
        tag="latest",
        digest="abc123",
        size_bytes=4_000_000_000,
    )

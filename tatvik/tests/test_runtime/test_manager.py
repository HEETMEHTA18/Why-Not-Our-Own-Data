from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_list_models(mock_ollama_client):
    from runtime.manager import ModelManager

    manager = ModelManager(mock_ollama_client)
    mock_ollama_client.list_models.return_value = []
    models = await manager.list_models()
    assert models == []


@pytest.mark.asyncio
async def test_get_runtime_stats(mock_ollama_client):
    from runtime.manager import ModelManager

    manager = ModelManager(mock_ollama_client)
    mock_ollama_client.health.return_value = True
    mock_ollama_client.version.return_value = "0.5.0"

    stats = await manager.get_runtime_stats()
    assert stats.ollama_running is True
    assert stats.ollama_version == "0.5.0"


@pytest.mark.asyncio
async def test_is_ollama_running(mock_ollama_client):
    from runtime.manager import ModelManager

    manager = ModelManager(mock_ollama_client)
    mock_ollama_client.health.return_value = True
    assert await manager.is_ollama_running() is True


@pytest.mark.asyncio
async def test_pull_model(mock_ollama_client):
    from runtime.manager import ModelManager

    manager = ModelManager(mock_ollama_client)
    async def mock_pull(name: str):
        yield {"status": "pulling manifest"}
        yield {"status": "downloading"}
        yield {"status": "success"}

    mock_ollama_client.pull_model = mock_pull
    status = await manager.pull_model("llama3.1:latest")
    assert status == "success"

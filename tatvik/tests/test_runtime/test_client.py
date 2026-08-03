from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_success():
    from runtime.client import OllamaClient

    client = OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    client._client.get.return_value = httpx.Response(200)

    result = await client.health()
    assert result is True
    await client.close()


@pytest.mark.asyncio
async def test_health_failure():
    client = __import__("runtime.client", fromlist=[""]).OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    client._client.get.side_effect = httpx.RequestError("Connection refused")

    result = await client.health()
    assert result is False
    await client.close()


@pytest.mark.asyncio
async def test_list_models():
    from runtime.client import OllamaClient

    client = OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    mock_req = MagicMock()
    client._client.get.return_value = httpx.Response(
        200, json={
            "models": [
                {
                    "name": "llama3.1:latest",
                    "model": "llama3.1:latest",
                    "size": 4000000000,
                    "digest": "abc123",
                    "modified_at": "2024-01-01T00:00:00Z",
                    "details": {},
                }
            ]
        }, request=mock_req,
    )

    models = await client.list_models()
    assert len(models) == 1
    assert models[0].name == "llama3.1:latest"
    await client.close()


@pytest.mark.asyncio
async def test_generate():
    from runtime.client import OllamaClient
    from runtime.models import GenerateRequest

    client = OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    client._client.post.return_value = httpx.Response(
        200, json={
            "model": "llama3.1:latest",
            "response": "Hello!",
            "done": True,
            "total_duration": 1000,
        }, request=MagicMock(),
    )

    req = GenerateRequest(model="llama3.1:latest", prompt="Hi")
    resp = await client.generate(req)
    assert resp.response == "Hello!"
    assert resp.done is True
    await client.close()


@pytest.mark.asyncio
async def test_chat():
    from runtime.client import OllamaClient
    from runtime.models import ChatMessage, ChatRequest

    client = OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    client._client.post.return_value = httpx.Response(
        200, json={
            "model": "llama3.1:latest",
            "message": {"role": "assistant", "content": "Hello!"},
            "done": True,
        }, request=MagicMock(),
    )

    req = ChatRequest(
        model="llama3.1:latest",
        messages=[ChatMessage(role="user", content="Hi")],
    )
    resp = await client.chat(req)
    assert resp.message.content == "Hello!"
    assert resp.done is True
    await client.close()


@pytest.mark.asyncio
async def test_version():
    from runtime.client import OllamaClient

    client = OllamaClient(host="http://test:11434")
    client._client = AsyncMock(spec=httpx.AsyncClient)
    client._client.get.return_value = httpx.Response(200, json={"version": "0.5.0"}, request=MagicMock())

    ver = await client.version()
    assert ver == "0.5.0"
    await client.close()

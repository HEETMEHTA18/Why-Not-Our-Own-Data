from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import settings
from shared.types import GPUInfo

from .models import (
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    GenerateRequest,
    GenerateResponse,
    ModelInfo,
)

logger = structlog.get_logger()


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        self.host = (host or settings.ollama_host).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.host,
            timeout=settings.ollama_request_timeout,
            headers={"Content-Type": "application/json"},
        )
        self._running = False

    async def __aenter__(self) -> OllamaClient:
        await self.health()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
    async def health(self) -> bool:
        try:
            r = await self._client.get("/")
            self._running = r.status_code == 200
            return self._running
        except httpx.RequestError:
            self._running = False
            return False

    async def list_models(self) -> list[ModelInfo]:
        r = await self._client.get("/api/tags")
        r.raise_for_status()
        return [ModelInfo(**m) for m in r.json().get("models", [])]

    async def show_model(self, name: str) -> dict[str, Any]:
        r = await self._client.post("/api/show", json={"name": name})
        r.raise_for_status()
        return r.json()

    async def pull_model(self, name: str) -> AsyncIterator[dict[str, Any]]:
        async with self._client.stream("POST", "/api/pull", json={"name": name}) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line.strip():
                    yield line

    async def delete_model(self, name: str) -> None:
        r = await self._client.delete("/api/delete", json={"name": name})
        r.raise_for_status()

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        r = await self._client.post("/api/generate", json=req.model_dump(exclude_none=True))
        r.raise_for_status()
        return GenerateResponse(**r.json())

    async def generate_stream(self, req: GenerateRequest) -> AsyncIterator[GenerateResponse]:
        async with self._client.stream(
            "POST", "/api/generate", json=req.model_dump(exclude_none=True)
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line.strip():
                    yield GenerateResponse(**line)

    async def chat(self, req: ChatRequest) -> ChatResponse:
        r = await self._client.post("/api/chat", json=req.model_dump(exclude_none=True))
        r.raise_for_status()
        return ChatResponse(**r.json())

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatResponse]:
        async with self._client.stream(
            "POST", "/api/chat", json=req.model_dump(exclude_none=True)
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line.strip():
                    yield ChatResponse(**line)

    async def embed(self, req: EmbedRequest) -> EmbedResponse:
        r = await self._client.post("/api/embed", json=req.model_dump(exclude_none=True))
        r.raise_for_status()
        return EmbedResponse(**r.json())

    async def version(self) -> str:
        r = await self._client.get("/api/version")
        r.raise_for_status()
        return r.json().get("version", "")

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def is_running(self) -> bool:
        return self._running

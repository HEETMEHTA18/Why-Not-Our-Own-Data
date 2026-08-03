from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from shared.config import settings
from .models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    GenerateRequest,
    GenerateResponse,
    ModelInfo,
)

logger = structlog.get_logger()


class LlamaClient:
    def __init__(self, host: str | None = None) -> None:
        self.host = (host or "http://localhost:11434").rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.host,
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )
        self._running = False

    async def __aenter__(self) -> LlamaClient:
        await self.health()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/health")
            self._running = r.status_code == 200
            return self._running
        except httpx.RequestError:
            self._running = False
            return False

    async def list_models(self) -> list[ModelInfo]:
        r = await self._client.get("/v1/models")
        r.raise_for_status()
        data = r.json()
        models = []
        for m in data.get("data", []):
            meta = m.get("meta", {})
            models.append(ModelInfo(
                name=m.get("id", "unknown"),
                model=m.get("id", "unknown"),
                size=meta.get("size", 0) or 0,
                digest="",
                modified_at=__import__("datetime").datetime.now(),
                details={"family": meta.get("type", ""), "parameter_size": str(meta.get("n_params", 0))},
            ))
        return models

    async def show_model(self, name: str) -> dict[str, Any]:
        return {"model": name, "details": "llama-server managed"}

    async def pull_model(self, name: str) -> AsyncIterator[dict[str, Any]]:
        yield {"status": "not supported on llama-server"}

    async def delete_model(self, name: str) -> None:
        pass

    async def generate(self, req: GenerateRequest) -> GenerateResponse:
        payload = {
            "model": req.model,
            "prompt": req.prompt,
            "max_tokens": 512,
            "temperature": 0.7,
            "stream": False,
        }
        if req.options:
            payload.update(req.options)
        r = await self._client.post("/v1/completions", json=payload)
        r.raise_for_status()
        data = r.json()
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})
        return GenerateResponse(
            model=req.model,
            response=choice.get("text", ""),
            done=True,
            prompt_eval_count=usage.get("prompt_tokens", 0),
            eval_count=usage.get("completion_tokens", 0),
        )

    async def generate_stream(self, req: GenerateRequest) -> AsyncIterator[GenerateResponse]:
        payload = {
            "model": req.model,
            "prompt": req.prompt,
            "max_tokens": 512,
            "temperature": 0.7,
            "stream": True,
        }
        if req.options:
            payload.update(req.options)
        async with self._client.stream("POST", "/v1/completions", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line.strip() and not line.startswith("data: [DONE]"):
                    yield GenerateResponse(
                        model=req.model,
                        response=line,
                        done=False,
                    )

    async def chat(self, req: ChatRequest) -> ChatResponse:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        payload = {
            "model": req.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": False,
        }
        if req.options:
            payload.update(req.options)
        r = await self._client.post("/v1/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        usage = data.get("usage", {})
        return ChatResponse(
            model=req.model,
            message=ChatMessage(role=msg.get("role", "assistant"), content=msg.get("content", "")),
            done=bool(choice.get("finish_reason") == "stop"),
            prompt_eval_count=usage.get("prompt_tokens", 0),
            eval_count=usage.get("completion_tokens", 0),
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatResponse]:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        payload = {
            "model": req.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": True,
        }
        if req.options:
            payload.update(req.options)
        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.strip() or not line.startswith("data: "):
                    continue
                if "[DONE]" in line:
                    yield ChatResponse(
                        model=req.model,
                        message=ChatMessage(role="assistant", content=""),
                        done=True,
                    )
                    break
                try:
                    chunk = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if not content:
                    continue
                yield ChatResponse(
                    model=req.model,
                    message=ChatMessage(role="assistant", content=content),
                    done=False,
                )

    async def embed(self, req: Any) -> Any:
        return type("EmbedResponse", (), {"model": req.model, "embeddings": []})()

    async def version(self) -> str:
        try:
            r = await self._client.get("/health")
            return "llama-server"
        except Exception:
            return ""

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def is_running(self) -> bool:
        return self._running

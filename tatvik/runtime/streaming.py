from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Callable

from runtime.client import OllamaClient
from runtime.models import ChatRequest, ChatResponse, GenerateRequest, GenerateResponse


class StreamManager:
    def __init__(self, client: OllamaClient) -> None:
        self._client = client
        self._active_streams: dict[str, asyncio.Task] = {}

    async def generate(
        self,
        req: GenerateRequest,
        on_token: Callable[[str], None] | None = None,
    ) -> AsyncIterator[str]:
        req.stream = True
        async for chunk in self._client.generate_stream(req):
            text = chunk.response if hasattr(chunk, "response") else ""
            if text and on_token:
                on_token(text)
            yield text

    async def chat(
        self,
        req: ChatRequest,
        on_token: Callable[[str], None] | None = None,
    ) -> AsyncIterator[str]:
        req.stream = True
        async for chunk in self._client.chat_stream(req):
            text = ""
            if hasattr(chunk, "message") and chunk.message:
                text = chunk.message.content or ""
            if text and on_token:
                on_token(text)
            yield text

    async def generate_sse(
        self,
        req: GenerateRequest,
    ) -> AsyncIterator[str]:
        req.stream = True
        async for chunk in self._client.generate_stream(req):
            data = chunk.model_dump()
            yield f"data: {json.dumps(data)}\n\n"
        yield "data: [DONE]\n\n"

    def cancel_stream(self, stream_id: str) -> None:
        task = self._active_streams.get(stream_id)
        if task and not task.done():
            task.cancel()
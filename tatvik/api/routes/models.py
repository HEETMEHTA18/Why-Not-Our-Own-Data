from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import Container, get_container
from runtime.models import ChatRequest, ChatMessage, ChatResponse, GenerateRequest, GenerateResponse, ModelInfo
from shared.config import settings
from shared.supercompress import get_client

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("")
async def list_models(container: Container = Depends(get_container)) -> list[ModelInfo]:
    return await container.model_manager.list_models()


@router.get("/{name:path}")
async def show_model(name: str, container: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        return await container.model_manager.show_model(name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pull")
async def pull_model(name: str, container: Container = Depends(get_container)) -> dict[str, str]:
    status = await container.model_manager.pull_model(name)
    return {"model": name, "status": status}


@router.delete("/{name:path}")
async def delete_model(name: str, container: Container = Depends(get_container)) -> dict[str, str]:
    await container.model_manager.delete_model(name)
    return {"model": name, "status": "deleted"}


@router.post("/generate")
async def generate(
    req: GenerateRequest, container: Container = Depends(get_container),
) -> GenerateResponse:
    try:
        return await container.llama_client.generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(
    req: ChatRequest, container: Container = Depends(get_container),
) -> ChatResponse:
    try:
        req = await _maybe_compress(req)
        return await container.llama_client.chat(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, container: Container = Depends(get_container),
) -> StreamingResponse:
    async def event_source():
        try:
            async for chunk in container.llama_client.chat_stream(req):
                if chunk.done:
                    yield "data: [DONE]\n\n"
                    break
                payload = json.dumps({"content": chunk.message.content})
                yield f"data: {payload}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runtime/stats")
async def runtime_stats(container: Container = Depends(get_container)) -> dict[str, Any]:
    stats = await container.model_manager.get_runtime_stats()
    return stats.model_dump()


async def _maybe_compress(req: ChatRequest) -> ChatRequest:
    """Compress non-user context before inference (query-aware, never raises).

    The final user message is preserved verbatim as the query; system + earlier
    history is the context to shrink. If compression is disabled/unavailable the
    request passes through untouched.
    """
    if not settings.supercompress_enabled or len(req.messages) < 2:
        return req

    last = req.messages[-1]
    if last.role != "user":
        return req

    context_msgs = req.messages[:-1]
    context = "\n\n".join(
        f"{m.role.upper()}: {m.content}" for m in context_msgs if m.content
    )
    if not context.strip():
        return req

    client = get_client()
    result = await client.acompress(context, last.content)
    if not result.compressed or result.compressed_text == context:
        return req

    compressed_msgs: list[ChatMessage] = [
        ChatMessage(role="system", content=result.compressed_text),
        last,
    ]
    return req.model_copy(update={"messages": compressed_msgs})

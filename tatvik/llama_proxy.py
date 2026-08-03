"""Minimal OpenAI-compatible server using llama-cpp-python."""
import os
import sys
import json
import time
import uuid
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
MODEL_PATH = WORKSPACE / "models" / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"

if not MODEL_PATH.exists():
    print(json.dumps({"error": f"Model not found: {MODEL_PATH}"}))
    sys.exit(1)

from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

from llama_cpp import Llama

llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=-1,
    verbose=False,
    chat_format="qwen",
)

app = FastAPI(title="llama-proxy")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "qwen2.5-coder-3b"
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "llama-proxy"


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen2.5-coder-3b",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "llama-proxy",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    resp = llm.create_chat_completion(
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    choice = resp["choices"][0]
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": choice["message"]["content"],
                },
                "finish_reason": choice.get("finish_reason", "stop"),
            }
        ],
        "usage": resp.get("usage", {}),
    }


@app.post("/v1/completions")
async def completions(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "")
    resp = llm.create_completion(prompt=prompt, max_tokens=body.get("max_tokens", 128))
    return {
        "id": f"cmpl-{uuid.uuid4().hex[:12]}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": body.get("model", "qwen2.5-coder-3b"),
        "choices": [
            {
                "text": resp["choices"][0]["text"],
                "index": 0,
                "finish_reason": resp["choices"][0].get("finish_reason", "stop"),
            }
        ],
        "usage": resp.get("usage", {}),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"status": "llama-proxy running"}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11434
    print(json.dumps({"event": "llama_proxy_starting", "model": str(MODEL_PATH), "port": port}))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

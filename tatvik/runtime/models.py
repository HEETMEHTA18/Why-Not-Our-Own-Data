from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str
    model: str
    size: int
    digest: str
    modified_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class ModelManifest(BaseModel):
    name: str
    tag: str
    digest: str
    layers: list[dict[str, Any]] = Field(default_factory=list)
    schema_version: int = 2
    media_type: str = "application/vnd.ollama.image.model.v2"


class RuntimeStats(BaseModel):
    model_loaded: str | None = None
    ollama_running: bool = False
    ollama_version: str = ""
    gpu_available: bool = False
    gpu_count: int = 0
    memory_usage_mb: int = 0
    uptime_seconds: float = 0.0


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: str | None = None
    template: str | None = None
    context: list[int] | None = None
    stream: bool = False
    raw: bool = False
    format: str | None = None
    keep_alive: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    model: str
    response: str
    done: bool
    context: list[int] | None = None
    total_duration: int = 0
    load_duration: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration: int = 0
    eval_count: int = 0
    eval_duration: int = 0


class ChatMessage(BaseModel):
    role: str
    content: str
    images: list[str] | None = None


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    format: str | None = None
    keep_alive: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    model: str
    message: ChatMessage
    done: bool
    total_duration: int = 0
    load_duration: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration: int = 0
    eval_count: int = 0
    eval_duration: int = 0


class EmbedRequest(BaseModel):
    model: str
    input: str | list[str]
    options: dict[str, Any] = Field(default_factory=dict)


class EmbedResponse(BaseModel):
    model: str
    embeddings: list[list[float]]

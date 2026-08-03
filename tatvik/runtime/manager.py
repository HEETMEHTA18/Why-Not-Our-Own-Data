from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from shared.config import settings
from shared.types import GPUInfo, Status

from .client import OllamaClient
from .models import ModelInfo, RuntimeStats

logger = structlog.get_logger()


class ModelManager:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()
        self._loaded_model: str | None = None
        self._start_time = datetime.now()

    async def list_models(self) -> list[ModelInfo]:
        return await self._client.list_models()

    async def show_model(self, name: str) -> dict[str, Any]:
        return await self._client.show_model(name)

    async def pull_model(self, name: str) -> str:
        last_status = ""
        async for update in self._client.pull_model(name):
            last_status = update.get("status", "")
            logger.info("model_pull_progress", model=name, status=last_status)
        logger.info("model_pull_complete", model=name)
        return last_status

    async def delete_model(self, name: str) -> None:
        await self._client.delete_model(name)
        logger.info("model_deleted", model=name)

    async def load_model(self, name: str) -> None:
        await self._client.generate(
            __import__("shared.types", fromlist=[""]).GenerateRequest(
                model=name, prompt="", keep_alive="-1"
            )
        )
        self._loaded_model = name
        logger.info("model_loaded", model=name)

    async def unload_model(self, name: str) -> None:
        await self._client.generate(
            __import__("shared.types", fromlist=[""]).GenerateRequest(
                model=name, prompt="", keep_alive="0"
            )
        )
        if self._loaded_model == name:
            self._loaded_model = None
        logger.info("model_unloaded", model=name)

    async def get_runtime_stats(self) -> RuntimeStats:
        try:
            running = await self._client.health()
            ver = await self._client.version() if running else ""
        except Exception:
            running = False
            ver = ""

        return RuntimeStats(
            model_loaded=self._loaded_model,
            ollama_running=running,
            ollama_version=ver,
            gpu_available=False,
            gpu_count=0,
            memory_usage_mb=0,
            uptime_seconds=(datetime.now() - self._start_time).total_seconds(),
        )

    async def is_ollama_running(self) -> bool:
        return await self._client.health()

    async def close(self) -> None:
        await self._client.close()

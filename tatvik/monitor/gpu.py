from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

import structlog

from shared.config import settings
from shared.types import GPUInfo

logger = structlog.get_logger()


class GPUMonitor:
    def __init__(self) -> None:
        self._pynvml_available = False
        self._check_pynvml()
        self._history: list[GPUInfo] = []
        self._max_history = 3600
        self._monitor_task: asyncio.Task[None] | None = None
        self._running = False
        self._on_update: list[Callable[[GPUInfo], None]] = []

    def _check_pynvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            self._pynvml_available = True
            logger.info("gpu_monitor_pynvml_available")
        except Exception:
            self._pynvml_available = False
            logger.warning("gpu_monitor_pynvml_not_available")

    def on_update(self, callback: Callable[[GPUInfo], None]) -> None:
        self._on_update.append(callback)

    async def start(self, interval_s: int | None = None) -> None:
        if self._monitor_task is not None:
            return
        self._running = True
        interval = interval_s or settings.gpu_monitor_interval_s
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("gpu_monitor_started", interval_s=interval)

    async def stop(self) -> None:
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("gpu_monitor_stopped")

    def get_current(self) -> GPUInfo | None:
        try:
            return self._query_gpu()
        except Exception:
            return None

    def get_history(self, limit: int = 100) -> list[GPUInfo]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        current = self.get_current()
        if not current:
            return {"available": False, "gpus": []}

        gpu_list = [current.model_dump()]
        if self._history:
            recent = self._history[-60:]
            avg_util = sum(g.utilization_pct for g in recent) / len(recent) if recent else 0
            avg_mem = sum(g.used_memory_mb for g in recent) / len(recent) if recent else 0
        else:
            avg_util = current.utilization_pct
            avg_mem = float(current.used_memory_mb)

        return {
            "available": True,
            "gpus": gpu_list,
            "avg_utilization_pct": round(avg_util, 1),
            "avg_memory_mb": round(avg_mem, 1),
            "total_memory_mb": current.total_memory_mb,
            "samples": len(self._history),
        }

    def is_gpu_available(self) -> bool:
        if not self._pynvml_available:
            return False
        try:
            info = self._query_gpu()
            return info is not None
        except Exception:
            return False

    def _query_gpu(self) -> GPUInfo | None:
        if not self._pynvml_available:
            return None

        import pynvml
        try:
            count = pynvml.nvmlDeviceGetCount()
            if count == 0:
                return None

            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle).decode() if isinstance(pynvml.nvmlDeviceGetName(handle), bytes) else pynvml.nvmlDeviceGetName(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, 0)

            return GPUInfo(
                index=0,
                name=name,
                total_memory_mb=mem.total // (1024 * 1024),
                used_memory_mb=mem.used // (1024 * 1024),
                free_memory_mb=mem.free // (1024 * 1024),
                utilization_pct=float(util.gpu),
                temperature_c=float(temp),
            )
        except Exception as e:
            logger.warning("gpu_query_failed", error=str(e))
            return None

    async def _monitor_loop(self, interval_s: int) -> None:
        while self._running:
            try:
                info = self._query_gpu()
                if info:
                    self._history.append(info)
                    if len(self._history) > self._max_history:
                        self._history = self._history[-self._max_history:]
                    for cb in self._on_update:
                        try:
                            cb(info)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("gpu_monitor_error", error=str(e))
            await asyncio.sleep(interval_s)

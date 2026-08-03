from __future__ import annotations

import asyncio
from datetime import datetime, time
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


class ScheduleTrigger:
    MANUAL = "manual"
    NIGHTLY = "nightly"
    IDLE = "idle"


class Scheduler:
    def __init__(self) -> None:
        self._nightly_task: asyncio.Task[None] | None = None
        self._idle_task: asyncio.Task[None] | None = None
        self._running = False
        self._on_nightly: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._on_idle: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._idle_check_interval = 60

    def set_nightly_callback(
        self,
        callback: Callable[[], Coroutine[Any, Any, None]] | None,
    ) -> None:
        self._on_nightly = callback

    def set_idle_callback(
        self,
        callback: Callable[[], Coroutine[Any, Any, None]] | None,
    ) -> None:
        self._on_idle = callback

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._nightly_task = asyncio.create_task(self._nightly_loop())
        self._idle_task = asyncio.create_task(self._idle_loop())
        logger.info("scheduler_started")

    async def stop(self) -> None:
        self._running = False
        for task in [self._nightly_task, self._idle_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("scheduler_stopped")

    async def _nightly_loop(self) -> None:
        while self._running:
            try:
                now = datetime.now()
                target = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if now >= target:
                    target = target.replace(day=target.day + 1)
                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                if self._on_nightly and self._running:
                    logger.info("nightly_trigger_fired")
                    await self._on_nightly()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("nightly_loop_error", error=str(e))
                await asyncio.sleep(60)

    async def _idle_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._idle_check_interval)
                if self._on_idle and self._running:
                    await self._on_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("idle_loop_error", error=str(e))
from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import uuid4

import structlog

from shared.types import JobType, Status

logger = structlog.get_logger()


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Job:
    def __init__(
        self,
        job_type: JobType,
        handler: Callable[..., Coroutine[Any, Any, Any]],
        params: dict[str, Any] | None = None,
        priority: int = 0,
        max_retries: int = 3,
        timeout: int = 7200,
    ) -> None:
        self.id: str = uuid4().hex[:12]
        self.job_type = job_type
        self.handler = handler
        self.params = params or {}
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.status = JobStatus.QUEUED
        self.retry_count = 0
        self.progress: float = 0.0
        self.result: Any = None
        self.error: str | None = None
        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self._cancel_event = asyncio.Event()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.status = JobStatus.CANCELLED


class JobQueue:
    def __init__(self, max_concurrent: int = 1) -> None:
        self._max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue[tuple[int, datetime, Job]] = asyncio.PriorityQueue()
        self._running: dict[str, Job] = {}
        self._completed: list[Job] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._worker_task: asyncio.Task[None] | None = None
        self._running_flag = False
        self._on_status_change: Callable[[Job], None] | None = None

    def set_status_callback(self, callback: Callable[[Job], None] | None) -> None:
        self._on_status_change = callback

    async def enqueue(self, job: Job) -> str:
        await self._queue.put((job.priority, datetime.now(), job))
        logger.info("job_enqueued", job_id=job.id, job_type=job.job_type.value)
        self._emit_status(job)
        return job.id

    async def start(self) -> None:
        if self._worker_task is not None:
            return
        self._running_flag = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("job_queue_started", max_concurrent=self._max_concurrent)

    async def stop(self) -> None:
        self._running_flag = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("job_queue_stopped")

    async def cancel_job(self, job_id: str) -> bool:
        for job in self._running.values():
            if job.id == job_id:
                job.cancel()
                return True
        return False

    def get_status(self, job_id: str) -> Job | None:
        for job in self._running.values():
            if job.id == job_id:
                return job
        for job in self._completed:
            if job.id == job_id:
                return job
        return None

    def list_jobs(self, limit: int = 50) -> list[Job]:
        running = sorted(self._running.values(), key=lambda j: j.created_at, reverse=True)
        completed = sorted(self._completed, key=lambda j: j.created_at, reverse=True)
        return (running + completed)[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "queued": self._queue.qsize(),
            "running": len(self._running),
            "completed": len([j for j in self._completed if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in self._completed if j.status == JobStatus.FAILED]),
            "max_concurrent": self._max_concurrent,
        }

    async def _worker_loop(self) -> None:
        while self._running_flag:
            try:
                _, _, job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            async with self._semaphore:
                if job._cancel_event.is_set():
                    job.status = JobStatus.CANCELLED
                    self._completed.append(job)
                    self._emit_status(job)
                    continue

                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                self._running[job.id] = job
                self._emit_status(job)

                try:
                    result = await asyncio.wait_for(
                        job.handler(**job.params),
                        timeout=job.timeout,
                    )
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    job.completed_at = datetime.now()
                    logger.info("job_completed", job_id=job.id)
                except asyncio.CancelledError:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                except Exception as e:
                    job.retry_count += 1
                    if job.retry_count < job.max_retries:
                        job.status = JobStatus.QUEUED
                        logger.warning("job_retrying", job_id=job.id, retry=job.retry_count, error=str(e))
                        await self._queue.put((job.priority, datetime.now(), job))
                    else:
                        job.status = JobStatus.FAILED
                        job.error = str(e)
                        job.completed_at = datetime.now()
                        logger.error("job_failed", job_id=job.id, error=str(e))
                finally:
                    self._running.pop(job.id, None)
                    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                        self._completed.append(job)
                    self._emit_status(job)

    def _emit_status(self, job: Job) -> None:
        if self._on_status_change:
            try:
                self._on_status_change(job)
            except Exception:
                pass

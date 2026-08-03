from __future__ import annotations

import asyncio

import pytest

from scheduler.queue import Job, JobQueue, JobStatus
from shared.types import JobType


@pytest.mark.asyncio
async def test_enqueue_and_run(job_queue):
    async def dummy_handler() -> str:
        return "done"

    job = Job(job_type=JobType.TRAINING, handler=dummy_handler)
    job_id = await job_queue.enqueue(job)
    assert job_id is not None

    await job_queue.start()
    await asyncio.sleep(0.1)
    await job_queue.stop()

    status = job_queue.get_status(job_id)
    assert status is not None
    assert status.status in (JobStatus.COMPLETED, JobStatus.RUNNING)


@pytest.mark.asyncio
async def test_job_failure_and_retry(job_queue):
    attempts = 0

    async def failing_handler() -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError(f"Attempt {attempts} failed")

    job = Job(job_type=JobType.TRAINING, handler=failing_handler, max_retries=2)
    await job_queue.enqueue(job)
    await job_queue.start()
    await asyncio.sleep(0.2)
    await job_queue.stop()

    assert job.status == JobStatus.FAILED
    assert job.error is not None


@pytest.mark.asyncio
async def test_list_jobs(job_queue):
    async def handler() -> str:
        return "ok"

    await job_queue.start()
    await job_queue.enqueue(Job(job_type=JobType.TRAINING, handler=handler))
    await job_queue.enqueue(Job(job_type=JobType.EVALUATION, handler=handler))
    await asyncio.sleep(0.1)

    jobs = job_queue.list_jobs()
    assert len(jobs) == 2
    await job_queue.stop()


@pytest.mark.asyncio
async def test_get_stats(job_queue):
    stats = job_queue.get_stats()
    assert stats["queued"] == 0
    assert stats["running"] == 0
    assert stats["max_concurrent"] == 2


@pytest.mark.asyncio
async def test_cancel_job(job_queue):
    cancelled_in_job = asyncio.Event()

    async def cancellable_handler() -> str:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled_in_job.set()
            raise

    job = Job(job_type=JobType.TRAINING, handler=cancellable_handler, timeout=30)
    await job_queue.start()
    await job_queue.enqueue(job)
    await asyncio.sleep(0.05)

    cancelled = await job_queue.cancel_job(job.id)
    assert cancelled is True
    await asyncio.sleep(0.05)
    assert job.status == JobStatus.CANCELLED
    await job_queue.stop()

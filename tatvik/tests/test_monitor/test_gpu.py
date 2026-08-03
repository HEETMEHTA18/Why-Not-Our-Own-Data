from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_gpu_monitor_init(gpu_monitor):
    assert gpu_monitor is not None


@pytest.mark.asyncio
async def test_gpu_monitor_start_stop(gpu_monitor):
    await gpu_monitor.start(interval_s=1)
    assert gpu_monitor._running is True
    await gpu_monitor.stop()
    assert gpu_monitor._running is False


def test_get_stats_no_gpu(gpu_monitor):
    stats = gpu_monitor.get_stats()
    assert "available" in stats


def test_is_gpu_available(gpu_monitor):
    result = gpu_monitor.is_gpu_available()
    assert isinstance(result, bool)

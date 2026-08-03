from __future__ import annotations

import pytest

from evaluation.models import BenchmarkConfig, BenchmarkTask


@pytest.mark.asyncio
async def test_simulate_eval(benchmark_runner):
    score, metrics, samples = await benchmark_runner.run_task(
        task=BenchmarkTask.MMLU,
        model_name="llama3.1-8b",
    )
    assert 0.0 <= score <= 1.0
    assert "acc" in metrics
    assert samples > 0


@pytest.mark.asyncio
async def test_simulate_eval_all_tasks(benchmark_runner):
    for task in BenchmarkTask:
        if task == BenchmarkTask.CUSTOM:
            continue
        score, metrics, samples = await benchmark_runner.run_task(
            task=task, model_name="test-model",
        )
        assert 0.0 <= score <= 1.0
        assert samples > 0


@pytest.mark.asyncio
async def test_benchmark_config_defaults():
    cfg = BenchmarkConfig()
    assert len(cfg.tasks) == 2
    assert cfg.tasks[0] == BenchmarkTask.MMLU
    assert cfg.tasks[1] == BenchmarkTask.GSM8K
    assert cfg.num_fewshot == 0
    assert cfg.batch_size == 8

#!/usr/bin/env python3
"""Seed the tatvik registry with sample data so the empty pages have content.

Populates: /registry/models, /training/adapters, /evaluation/benchmarks, /experiments.
Benchmarks are SIMULATED (lm_eval not installed) — no GPU or model download required.
Run from repo root with: source .venv/bin/activate && python scripts/seed_tatvik.py
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "tatvik")

from api.deps import Container
from evaluation.models import BenchmarkConfig, BenchmarkTask
from shared.types import Status

BASE_MODEL = "qwen2.5-coder-3b-instruct"


async def main() -> None:
    c = Container()
    await c.initialize()

    existing = await c.registry_manager.get_base_models()
    if any(b.name == BASE_MODEL for b in existing):
        print(f"base model '{BASE_MODEL}' already registered, skipping seed")
        await c.shutdown()
        return

    print("1. registering base model ...")
    bm = await c.registry_manager.register_base_model(
        name=BASE_MODEL,
        tag="latest",
        size_bytes=2_148_000_000,
        metadata={"family": "qwen2.5", "params": "3B", "quantization": "q4_k_m", "source": "local-gguf"},
    )
    print(f"   -> {bm.id} ({bm.name})")

    print("2. creating adapters ...")
    a1 = await c.registry_manager.create_adapter(
        base_model_id=bm.id,
        dataset_id="instruct-human-feedback",
        training_config={"lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "epochs": 3},
        notes="baseline LoRA run",
    )
    await c.registry_manager.update_adapter_status(
        a1.id, Status.COMPLETED,
        metrics={"accuracy": 0.742, "eval_score": 0.76, "final_loss": 0.31, "latency": 42, "samples": 12400},
    )
    await c.registry_manager.update_adapter_path(a1.id, "models/adapters/qwen-lora-v1")
    print(f"   -> {a1.id} v{a1.version} COMPLETED")

    a2 = await c.registry_manager.create_adapter(
        base_model_id=bm.id,
        dataset_id="code-qa-pairs",
        training_config={"lora_r": 32, "lora_alpha": 64, "lora_dropout": 0.1, "epochs": 5},
        parent_adapter_id=a1.id,
        notes="higher-rank + longer run",
    )
    await c.registry_manager.update_adapter_status(
        a2.id, Status.COMPLETED,
        metrics={"accuracy": 0.781, "eval_score": 0.80, "final_loss": 0.24, "latency": 51, "samples": 21300},
    )
    await c.registry_manager.update_adapter_path(a2.id, "models/adapters/qwen-lora-v2")
    print(f"   -> {a2.id} v{a2.version} COMPLETED")

    print("3. running simulated benchmark evals ...")
    cfg = BenchmarkConfig(
        tasks=[BenchmarkTask.MMLU, BenchmarkTask.GSM8K, BenchmarkTask.HUMAN_EVAL],
        num_fewshot=0,
    )
    base_res = await c.benchmark_engine.evaluate(base_model=BASE_MODEL, config=cfg)
    for r in base_res:
        print(f"   base  {r.task}: {r.score:.3f}")
    adapter_res = await c.benchmark_engine.evaluate(
        base_model=BASE_MODEL, adapter_path=a2.path, config=cfg,
    )
    for r in adapter_res:
        print(f"   v2    {r.task}: {r.score:.3f}")

    print("4. creating experiments ...")
    e1 = await c.registry_manager.create_experiment(
        experiment_type="lora-rank-ablation",
        base_model_id=bm.id,
        adapter_id=a2.id,
        config={"configs": [16, 32], "epochs": [3, 5]},
    )
    await c.registry_manager.update_experiment(
        e1.id, Status.COMPLETED,
        metrics={"eval_score": 0.80, "accuracy": 0.781, "loss": 0.24},
    )
    e2 = await c.registry_manager.create_experiment(
        experiment_type="quantization-comparison",
        base_model_id=bm.id,
        config={"configs": ["q4_k_m", "q8_0"]},
    )
    await c.registry_manager.update_experiment(
        e2.id, Status.COMPLETED,
        metrics={"eval_score": 0.76, "accuracy": 0.742, "loss": 0.31},
    )
    print(f"   -> {e1.id} COMPLETED ({e1.experiment_type})")
    print(f"   -> {e2.id} COMPLETED ({e2.experiment_type})")

    await c.shutdown()
    print("\nDone. Pages now show content: /registry/models, /training/adapters, /evaluation/benchmarks, /experiments")


if __name__ == "__main__":
    asyncio.run(main())

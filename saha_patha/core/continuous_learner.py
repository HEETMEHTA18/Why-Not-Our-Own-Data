from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .config import SahapathaConfig
from .data_collector import DataCollector
from .dataset_manager import DatasetManager
from .training_engine import TrainingEngine
from .model_registry import ModelRegistry
from .inference_engine import InferenceEngine
from .eval_harness import EvalHarness


class Sahapatha:
    def __init__(self, config: SahapathaConfig | None = None):
        self.config = config or SahapathaConfig()
        self.collector = DataCollector(storage_dir=f"{self.config.dataset_dir}/buffer")
        self.datasets = DatasetManager(dataset_dir=self.config.dataset_dir)
        self.training = TrainingEngine(self.config)
        self.registry = ModelRegistry(registry_dir=self.config.adapter_dir)
        self.inference = InferenceEngine(self.config)
        self.eval_harness = EvalHarness(self.config)
        self._last_train_time: float | None = None

    def learn(self, prompt: str, response: str, metadata: dict | None = None) -> str:
        interaction = self.collector.record(prompt, response, metadata)
        count = self.collector.count()
        can_train = (
            count >= self.config.min_samples_for_training
            and (self._last_train_time is None
                 or time.time() - self._last_train_time >= self.config.min_interval_hours * 3600)
        )
        if can_train:
            self._run_training()
        return interaction.interaction_id

    def answer(self, prompt: str, use_adapter: bool = True, **kwargs) -> str:
        if use_adapter:
            latest = self.registry.get_latest(self.config.base_model)
            if latest:
                self.inference.load_adapter()
            else:
                self.inference.load_base()
        else:
            self.inference.load_base()
        return self.inference.generate(prompt, **kwargs)

    def _run_training(self) -> dict[str, Any]:
        print(f"[Sahapatha] Starting training cycle...")
        buffer_path = f"{self.config.dataset_dir}/training_data_{int(time.time())}.json"
        count = self.collector.flush(buffer_path)
        if count == 0:
            print("[Sahapatha] No new data to train on.")
            return {"status": "skipped", "reason": "no_data"}
        print(f"[Sahapatha] Collected {count} new interactions.")
        interactions = self.datasets.load(Path(buffer_path).stem)
        deduped = self.datasets.deduplicate(interactions, self.config.collector.dedup_threshold)
        formatted = self.datasets.format_for_training(deduped)
        dataset_path = self.datasets.save(formatted, f"training_{int(time.time())}")
        print(f"[Sahapatha] Dataset saved: {dataset_path} ({len(formatted)} examples)")
        result = self.training.train(str(dataset_path))
        adapter_name = result.get("adapter_name", "")
        version = self.registry.register(
            self.config.base_model,
            result["output_path"],
            result.get("metrics"),
        )
        print(f"[Sahapatha] Adapter registered: {version}")
        eval_results = self.eval_harness.evaluate(self.inference, version)
        print(f"[Sahapatha] Eval complete: {json.dumps({k: v['accuracy'] for k, v in eval_results.items()})}")
        self._last_train_time = time.time()
        return {
            "status": "completed",
            "version": version,
            "samples": count,
            "metrics": result.get("metrics"),
            "eval": eval_results,
        }

    def status(self) -> dict[str, Any]:
        buffer_count = self.collector.count()
        versions = self.registry.list(self.config.base_model)
        latest = self.registry.get_latest(self.config.base_model)
        return {
            "buffer_size": buffer_count,
            "ready_to_train": buffer_count >= self.config.min_samples_for_training,
            "total_versions": len(versions),
            "latest_version": latest["version"] if latest else None,
            "last_train_metrics": latest.get("metrics") if latest else None,
            "last_train_time": self._last_train_time,
            "base_model": self.config.base_model,
        }

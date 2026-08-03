from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


class DatasetManager:
    def __init__(self, dataset_dir: str = "saha_patha/datasets"):
        self._dataset_dir = Path(dataset_dir)
        self._dataset_dir.mkdir(parents=True, exist_ok=True)

    def save(self, interactions: list[dict], name: str) -> Path:
        path = self._dataset_dir / f"{name}.json"
        with open(path, "w") as f:
            json.dump(interactions, f, indent=2)
        return path

    def load(self, name: str) -> list[dict]:
        path = self._dataset_dir / f"{name}.json"
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    def deduplicate(self, interactions: list[dict], threshold: float = 0.85) -> list[dict]:
        if not interactions:
            return []
        kept = [interactions[0]]
        for item in interactions[1:]:
            p1 = item.get("prompt", "")[:50]
            if not any(self._similarity(p1, k.get("prompt", "")[:50]) > threshold for k in kept):
                kept.append(item)
        return kept

    def split(self, interactions: list[dict], ratio: float = 0.9) -> tuple[list[dict], list[dict]]:
        shuffled = list(interactions)
        random.shuffle(shuffled)
        split = int(len(shuffled) * ratio)
        return shuffled[:split], shuffled[split:]

    def format_for_training(self, interactions: list[dict]) -> list[dict]:
        result = []
        for item in interactions:
            prompt = item.get("prompt", "")
            response = item.get("response", "")
            if prompt and response:
                result.append({
                    "instruction": prompt,
                    "input": "",
                    "output": response,
                })
        return result

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        chars = set(a) | set(b)
        if not chars:
            return 1.0
        matches = sum(1 for c in chars if c in a and c in b)
        return matches / len(chars)

    def stats(self, name: str) -> dict:
        data = self.load(name)
        return {
            "name": name,
            "total": len(data),
            "avg_prompt_len": sum(len(d.get("prompt", "")) for d in data) / max(len(data), 1),
            "avg_response_len": sum(len(d.get("response", "")) for d in data) / max(len(data), 1),
        }

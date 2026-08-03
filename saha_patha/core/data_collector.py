from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Interaction:
    def __init__(self, prompt: str, response: str, metadata: dict | None = None):
        self.prompt = prompt
        self.response = response
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.interaction_id = hashlib.sha256(
            (self.timestamp + prompt + response[:100]).encode()
        ).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "interaction_id": self.interaction_id,
            "prompt": self.prompt,
            "response": self.response,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class DataCollector:
    def __init__(self, storage_dir: str = "saha_patha/datasets/buffer"):
        self._buffer_dir = Path(storage_dir)
        self._buffer_dir.mkdir(parents=True, exist_ok=True)
        self._buffer_file = self._buffer_dir / "interactions.jsonl"

    def record(self, prompt: str, response: str, metadata: dict | None = None) -> Interaction:
        interaction = Interaction(prompt, response, metadata)
        with open(self._buffer_file, "a") as f:
            f.write(json.dumps(interaction.to_dict()) + "\n")
        return interaction

    def flush(self, output_path: str) -> int:
        buffer = self._buffer_file
        if not buffer.exists():
            return 0
        interactions = [json.loads(l) for l in buffer.read_text().strip().splitlines() if l.strip()]
        if not interactions:
            return 0
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(interactions, f, indent=2)
        buffer.unlink()
        return len(interactions)

    def count(self) -> int:
        buffer = self._buffer_file
        if not buffer.exists():
            return 0
        return len([l for l in buffer.read_text().strip().splitlines() if l.strip()])

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ModelRegistry:
    def __init__(self, registry_dir: str = "saha_patha/adapters"):
        self._registry_dir = Path(registry_dir)
        self._registry_dir.mkdir(parents=True, exist_ok=True)

    def register(self, base_model: str, adapter_path: str, metrics: dict | None = None) -> str:
        version = self._next_version(base_model)
        entry = {
            "version": version,
            "base_model": base_model,
            "adapter_path": adapter_path,
            "metrics": metrics or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        record_path = self._registry_dir / base_model.replace("/", "-") / f"v{version}"
        record_path.mkdir(parents=True, exist_ok=True)
        with open(record_path / "registry.json", "w") as f:
            json.dump(entry, f, indent=2)
        return f"v{version}"

    def _next_version(self, base_model: str) -> int:
        model_dir = self._registry_dir / base_model.replace("/", "-")
        if not model_dir.exists():
            return 1
        versions = [int(d.name[1:]) for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        return max(versions) + 1 if versions else 1

    def list(self, base_model: str | None = None) -> list[dict]:
        if base_model:
            model_dir = self._registry_dir / base_model.replace("/", "-")
            if not model_dir.exists():
                return []
            versions = []
            for d in sorted(model_dir.iterdir(), key=lambda x: x.name):
                if d.is_dir() and d.name.startswith("v"):
                    reg_file = d / "registry.json"
                    if reg_file.exists():
                        versions.append(json.loads(reg_file.read_text()))
            return versions
        all_versions = []
        for model_dir in sorted(self._registry_dir.iterdir()):
            if model_dir.is_dir():
                for v_dir in model_dir.iterdir():
                    if v_dir.is_dir() and v_dir.name.startswith("v"):
                        reg_file = v_dir / "registry.json"
                        if reg_file.exists():
                            all_versions.append(json.loads(reg_file.read_text()))
        return all_versions

    def get_latest(self, base_model: str) -> dict | None:
        versions = self.list(base_model)
        return versions[-1] if versions else None

    def get(self, base_model: str, version: str | int) -> dict | None:
        dir_name = str(version)
        if dir_name.isdigit():
            dir_name = f"v{dir_name}"
        model_dir = self._registry_dir / base_model.replace("/", "-") / dir_name
        reg_file = model_dir / "registry.json"
        if reg_file.exists():
            return json.loads(reg_file.read_text())
        return None

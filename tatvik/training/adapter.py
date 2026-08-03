from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from shared.config import settings

logger = structlog.get_logger()


class AdapterManager:
    def __init__(self) -> None:
        self._adapters_dir = settings.adapters_dir

    def save_adapter_metadata(
        self, adapter_id: str, base_model: str, version: int,
        config: dict[str, Any], metrics: dict[str, float],
    ) -> Path:
        adapter_dir = self._adapters_dir / base_model.replace("/", "-").replace(":", "-") / f"v{version}"
        adapter_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "adapter_id": adapter_id,
            "base_model": base_model,
            "version": version,
            "config": config,
            "metrics": metrics,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        meta_path = adapter_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2))
        logger.info("adapter_metadata_saved", path=str(meta_path))
        return adapter_dir

    def get_adapter_path(self, base_model: str, version: int) -> Path | None:
        adapter_dir = self._adapters_dir / base_model.replace("/", "-").replace(":", "-") / f"v{version}"
        if adapter_dir.exists() and (adapter_dir / "metadata.json").exists():
            return adapter_dir
        return None

    def list_adapters(self, base_model: str) -> list[dict[str, Any]]:
        base_dir = self._adapters_dir / base_model.replace("/", "-").replace(":", "-")
        if not base_dir.exists():
            return []
        versions = []
        for d in sorted(base_dir.iterdir()):
            if d.is_dir() and d.name.startswith("v"):
                meta_file = d / "metadata.json"
                if meta_file.exists():
                    versions.append(json.loads(meta_file.read_text()))
        return versions

    def adapter_exists(self, base_model: str, version: int) -> bool:
        return self.get_adapter_path(base_model, version) is not None

    def delete_adapter(self, base_model: str, version: int) -> bool:
        path = self.get_adapter_path(base_model, version)
        if path:
            import shutil
            shutil.rmtree(path)
            logger.info("adapter_deleted", path=str(path))
            return True
        return False

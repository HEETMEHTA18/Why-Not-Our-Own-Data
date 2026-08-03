from __future__ import annotations

import json

import pytest

from shared.config import settings


def test_save_adapter_metadata(adapter_manager):
    adapter_dir = adapter_manager.save_adapter_metadata(
        adapter_id="test-123",
        base_model="llama3.1-8b",
        version=1,
        config={"learning_rate": 2e-4},
        metrics={"loss": 0.5},
    )
    assert adapter_dir.exists()
    meta_file = adapter_dir / "metadata.json"
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text())
    assert meta["adapter_id"] == "test-123"
    assert meta["version"] == 1


def test_get_adapter_path_not_exists(adapter_manager):
    path = adapter_manager.get_adapter_path("nonexistent", 1)
    assert path is None


def test_list_adapters_empty(adapter_manager):
    adapters = adapter_manager.list_adapters("nonexistent")
    assert adapters == []


def test_list_adapters(adapter_manager):
    adapter_manager.save_adapter_metadata(
        adapter_id="test-123", base_model="llama3.1-8b",
        version=1, config={}, metrics={"loss": 0.5},
    )
    adapters = adapter_manager.list_adapters("llama3.1-8b")
    assert len(adapters) == 1
    assert adapters[0]["adapter_id"] == "test-123"


def test_adapter_exists(adapter_manager):
    adapter_manager.save_adapter_metadata(
        adapter_id="test-123", base_model="llama3.1-8b",
        version=1, config={}, metrics={},
    )
    assert adapter_manager.adapter_exists("llama3.1-8b", 1) is True
    assert adapter_manager.adapter_exists("llama3.1-8b", 2) is False


def test_delete_adapter(adapter_manager):
    adapter_manager.save_adapter_metadata(
        adapter_id="test-123", base_model="llama3.1-8b",
        version=1, config={}, metrics={},
    )
    assert adapter_manager.delete_adapter("llama3.1-8b", 1) is True
    assert adapter_manager.adapter_exists("llama3.1-8b", 1) is False

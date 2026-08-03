from __future__ import annotations

import pytest

from training.config import LoraConfig, QuantizationConfig, Quantization, TrainingConfig


def test_lora_config_defaults():
    cfg = LoraConfig()
    assert cfg.r == 16
    assert cfg.lora_alpha == 32
    assert cfg.lora_dropout == 0.05
    assert cfg.task_type == "CAUSAL_LM"


def test_quantization_config_defaults():
    cfg = QuantizationConfig()
    assert cfg.method == Quantization.NF4
    assert cfg.compute_dtype == "bfloat16"
    assert cfg.use_double_quant is True


def test_training_config_defaults():
    cfg = TrainingConfig(
        model_name="llama3.1-8b",
        dataset_path="/tmp/test.json",
    )
    assert cfg.num_epochs == 3
    assert cfg.learning_rate == 2e-4
    assert cfg.batch_size == 4
    assert cfg.use_unsloth is True
    assert cfg.output_dir != ""
    assert cfg.adapter_name != ""


def test_training_config_post_init_sets_defaults():
    cfg = TrainingConfig(
        model_name="llama3.1-8b",
        dataset_path="/tmp/test.json",
    )
    assert "adapters" in cfg.output_dir
    assert cfg.output_dir != ""

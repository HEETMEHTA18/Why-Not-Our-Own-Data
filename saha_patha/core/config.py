from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class LoraParams:
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] | None = None


@dataclass
class TrainingParams:
    num_epochs: int = 5
    learning_rate: float = 2e-4
    batch_size: int = 1
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    warmup_steps: int = 10
    logging_steps: int = 5
    save_steps: int = 0
    optim: str = "adamw_8bit"
    lr_scheduler: str = "cosine"
    weight_decay: float = 0.01
    lora: LoraParams = field(default_factory=LoraParams)


@dataclass
class CollectorParams:
    max_history: int = 1000
    min_text_length: int = 10
    dedup_threshold: float = 0.85
    auto_curate: bool = True


@dataclass
class EvalParams:
    benchmarks: list[str] = field(default_factory=lambda: ["humaneval", "mbpp"])
    max_samples: int = 50
    temperature: float = 0.2


@dataclass
class SahapathaConfig:
    base_model: str = "deepseek-ai/deepseek-coder-6.7b-instruct"
    adapter_dir: str = "saha_patha/adapters"
    dataset_dir: str = "saha_patha/datasets"
    device: str = "auto"
    load_in_4bit: bool = True
    quant_type: str = "nf4"
    training: TrainingParams = field(default_factory=TrainingParams)
    collector: CollectorParams = field(default_factory=CollectorParams)
    evaluation: EvalParams = field(default_factory=EvalParams)
    use_unsloth: bool = False
    min_interval_hours: float = 1.0
    min_samples_for_training: int = 10

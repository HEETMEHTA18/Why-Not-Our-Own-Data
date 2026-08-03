from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Quantization(str, Enum):
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    NF4 = "nf4"
    FP4 = "fp4"


class LoraConfig(BaseModel):
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] | None = Field(
        default=None,
        description="None = default set (q_proj, v_proj, etc.)",
    )
    bias: Literal["none", "all", "lora_only"] = "none"
    task_type: str = "CAUSAL_LM"
    use_rslora: bool = False
    init_lora_weights: bool = True


class QuantizationConfig(BaseModel):
    method: Quantization = Quantization.NF4
    compute_dtype: Literal["float16", "bfloat16", "float32"] = "bfloat16"
    use_double_quant: bool = True


class TrainingConfig(BaseModel):
    model_name: str
    dataset_path: str
    dataset_format: str = "sharegpt"

    output_dir: str = ""
    adapter_name: str = ""

    lora: LoraConfig = Field(default_factory=LoraConfig)
    quantization: QuantizationConfig = Field(default_factory=QuantizationConfig)

    num_epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100

    use_unsloth: bool = True
    use_gradient_checkpointing: bool = True
    optim: str = "adamw_8bit"
    lr_scheduler_type: str = "cosine"
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    seed: int = 42

    resume_from_checkpoint: str | None = None
    checkpoint_dir: str = ""

    def model_post_init(self, __context: object) -> None:
        import json
        if not self.output_dir:
            self.output_dir = f"data/adapters/{self.model_name.replace('/', '-').replace(':', '-')}"
        if not self.adapter_name:
            self.adapter_name = f"adapter-{__import__('uuid').uuid4().hex[:8]}"

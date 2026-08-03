from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BenchmarkTask(str, Enum):
    MMLU = "mmlu"
    GSM8K = "gsm8k"
    HELLASWAG = "hellaswag"
    ARC_CHALLENGE = "arc_challenge"
    ARC_EASY = "arc_easy"
    BOOLQ = "boolq"
    PIQA = "piqa"
    WINOGROUND = "winoground"
    TRUTHLYQA = "truthfulqa_mc2"
    HUMAN_EVAL = "human_eval"
    MT_BENCH = "mt_bench"
    ALPACA_EVAL = "alpaca_eval"
    CUSTOM = "custom"


class BenchmarkConfig(BaseModel):
    tasks: list[BenchmarkTask] = Field(default_factory=lambda: [BenchmarkTask.MMLU, BenchmarkTask.GSM8K])
    num_fewshot: int = 0
    batch_size: int = 8
    limit: int | None = None
    use_chat_template: bool = True
    model_args: dict[str, Any] = Field(default_factory=dict)
    output_path: str = ""
    random_seed: int = 42


class BenchmarkSuite(BaseModel):
    name: str
    description: str = ""
    tasks: list[BenchmarkTask]


STANDARD_SUITES: dict[str, BenchmarkSuite] = {
    "quick": BenchmarkSuite(
        name="quick",
        description="Quick sanity check (2 tasks)",
        tasks=[BenchmarkTask.MMLU, BenchmarkTask.GSM8K],
    ),
    "standard": BenchmarkSuite(
        name="standard",
        description="Standard evaluation (5 tasks)",
        tasks=[
            BenchmarkTask.MMLU, BenchmarkTask.GSM8K, BenchmarkTask.HELLASWAG,
            BenchmarkTask.ARC_CHALLENGE, BenchmarkTask.BOOLQ,
        ],
    ),
    "full": BenchmarkSuite(
        name="full",
        description="Full evaluation suite (10 tasks)",
        tasks=[
            BenchmarkTask.MMLU, BenchmarkTask.GSM8K, BenchmarkTask.HELLASWAG,
            BenchmarkTask.ARC_CHALLENGE, BenchmarkTask.ARC_EASY,
            BenchmarkTask.BOOLQ, BenchmarkTask.PIQA, BenchmarkTask.WINOGROUND,
            BenchmarkTask.TRUTHLYQA, BenchmarkTask.HUMAN_EVAL,
        ],
    ),
}

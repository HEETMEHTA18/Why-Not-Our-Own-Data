from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TATVIK_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    ollama_host: str = "http://localhost:11434"
    ollama_request_timeout: int = 300

    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    adapters_dir: Path = data_dir / "adapters"
    experiments_dir: Path = data_dir / "experiments"
    benchmarks_dir: Path = data_dir / "benchmarks"
    registry_db: Path = data_dir / "registry" / "registry.db"
    registry_db_url: str = ""

    log_level: str = "INFO"
    log_json: bool = True

    training_default_model: str = "llama3.1-8b-instruct"
    training_default_epochs: int = 3
    training_default_lr: float = 2e-4
    training_default_batch_size: int = 4
    training_default_lora_r: int = 16
    training_default_lora_alpha: int = 32
    training_default_lora_dropout: float = 0.05
    training_max_concurrent: int = 1
    training_resumable: bool = True

    gpu_monitor_interval_s: int = 5

    scheduler_poll_interval_s: int = 10
    scheduler_max_retries: int = 3

    benchmark_default_tasks: str = "mmlu,gsm8k,hellaswag"
    benchmark_reject_threshold: float = -0.02

    registry_adapter_retention: int = 10

    supercompress_enabled: bool = True
    supercompress_api_key: str = ""
    supercompress_host: str = "https://www.supercompress.dev"
    supercompress_min_tokens: int = 100
    supercompress_timeout: float = 10.0

    @property
    def resolved_registry_db_url(self) -> str:
        return self.registry_db_url or f"sqlite+aiosqlite:///{self.registry_db}"

    def model_post_init(self, __context: object) -> None:
        for d in [self.data_dir, self.adapters_dir, self.experiments_dir, self.benchmarks_dir, self.registry_db.parent]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()

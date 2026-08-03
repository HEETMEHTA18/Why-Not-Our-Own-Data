from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class HermesSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HERMES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8101
    log_level: str = "INFO"
    governor_url: str = "http://localhost:8100"
    auto_init_pipelines: bool = True
    auto_init_scheduler_jobs: bool = True
    agent_timeout_seconds: int = 300
    max_concurrent_agents: int = 3
    event_bus_buffer: int = 1000


settings = HermesSettings()
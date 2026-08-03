from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Tatvik Governor"
    version: str = "0.1.0"
    debug: bool = True

    data_dir: Path = Path("data")
    sqlite_path: Path = data_dir / "governor.db"
    duckdb_path: Path = data_dir / "analytics.duckdb"
    chroma_path: Path = data_dir / "chroma"
    faiss_index_path: Path = data_dir / "faiss_index.bin"

    embedding_model: str = "all-MiniLM-L6-v2"
    quality_threshold: float = 0.7
    min_examples_for_training: int = 50
    min_quality_for_training: float = 0.80
    training_cooldown_days: int = 7
    max_contradiction_ratio: float = 0.15

    supercompress_enabled: bool = True
    supercompress_api_key: str = ""
    supercompress_host: str = "https://www.supercompress.dev"
    supercompress_min_tokens: int = 100
    supercompress_timeout: float = 10.0

    class Config:
        env_prefix = "TATVIK_"
        env_file = ".env"


settings = Settings()

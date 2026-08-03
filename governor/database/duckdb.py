import duckdb
from pathlib import Path
from typing import Optional, Any
from ..config import settings


class DuckDBStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.duckdb_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self):
        self._conn = duckdb.connect(str(self.db_path))
        self._init_views()
        return self

    def close(self):
        if self._conn:
            self._conn.close()

    def _init_views(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS dataset_analytics (
                run_id TEXT PRIMARY KEY,
                total_examples INTEGER,
                avg_quality DOUBLE,
                median_quality DOUBLE,
                std_quality DOUBLE,
                duplicate_count INTEGER,
                contradiction_count INTEGER,
                category_counts TEXT,
                score_distribution TEXT,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def execute(self, sql: str, params: list = None):
        if not self._conn:
            self.connect()
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)

    def query(self, sql: str, params: list = None):
        return self.execute(sql, params).fetchall()

    def query_df(self, sql: str):
        return self._conn.execute(sql).fetchdf()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

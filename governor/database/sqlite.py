import sqlite3
import tempfile
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Union
from ..config import settings


class SQLiteStore:
    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        raw = db_path if db_path is not None else settings.sqlite_path
        if isinstance(raw, str) and raw == ":memory:":
            self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            self.db_path = self._tmp.name
            self._tmp.close()
        else:
            self._tmp = None
            self.db_path = str(raw)
            if hasattr(raw, "parent"):
                raw.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with self.conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    latency_ms REAL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    rating INTEGER DEFAULT 0,
                    corrected_response TEXT,
                    correction_timestamp TEXT,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS dataset_examples (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    instruction TEXT NOT NULL,
                    input TEXT DEFAULT '',
                    output TEXT NOT NULL,
                    source TEXT DEFAULT 'correction',
                    created_at TEXT NOT NULL,
                    quality_score REAL DEFAULT 0.0,
                    is_valid INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );

                CREATE TABLE IF NOT EXISTS quality_scores (
                    id TEXT PRIMARY KEY,
                    example_id TEXT NOT NULL,
                    overall REAL NOT NULL,
                    coherence REAL DEFAULT 0.0,
                    correctness REAL DEFAULT 0.0,
                    completeness REAL DEFAULT 0.0,
                    novelty REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    importance REAL DEFAULT 0.0,
                    consistency REAL DEFAULT 0.0,
                    difficulty REAL DEFAULT 0.0,
                    scored_at TEXT NOT NULL,
                    FOREIGN KEY (example_id) REFERENCES dataset_examples(id)
                );

                CREATE TABLE IF NOT EXISTS training_recommendations (
                    id TEXT PRIMARY KEY,
                    recommended_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    example_count INTEGER DEFAULT 0,
                    avg_quality REAL DEFAULT 0.0,
                    estimated_improvement REAL DEFAULT 0.0,
                    estimated_duration_min INTEGER DEFAULT 0,
                    contradiction_count INTEGER DEFAULT 0,
                    duplicate_count INTEGER DEFAULT 0,
                    diversity_score REAL DEFAULT 0.0,
                    days_since_last_training REAL DEFAULT 0.0,
                    decision_log TEXT DEFAULT '{}',
                    approved_at TEXT,
                    rejected_at TEXT
                );

                CREATE TABLE IF NOT EXISTS classification_log (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    classification TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    reason TEXT DEFAULT '',
                    classified_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_session
                    ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                    ON conversations(timestamp);
                CREATE INDEX IF NOT EXISTS idx_dataset_quality
                    ON dataset_examples(quality_score);
                CREATE INDEX IF NOT EXISTS idx_recommendations_status
                    ON training_recommendations(status);
            """)

    @contextmanager
    def conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()):
        with self.conn() as conn:
            return conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()):
        with self.conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()):
        with self.conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

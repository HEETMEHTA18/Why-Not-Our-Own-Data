"""
GPU/cost telemetry, alerting, and the personalized learning profiler.

telemetry:  tracks GPU hours + est. cost per adapter/run so the platform can
            report cost-per-benchmark-point-improvement (ROI).
alerts:     lightweight rule engine that emits ALERT_TRIGGERED events +
            optional webhook notifications on regression/failures.
profiler:   learns the user's dominant stack from interactions and biases
            research + benchmark selection toward it.
"""

import uuid
import json
import structlog
from datetime import datetime, timezone
from typing import Optional, List, Dict

from .database.sqlite import SQLiteStore
from .eventbus.bus import get_bus
from .eventbus.models import EventType, EventPriority

logger = structlog.get_logger()

GPU_COST_PER_HOUR = 2.00  # placeholder $/hr; configurable


class CostTelemetry:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS gpu_runs (
                id TEXT PRIMARY KEY,
                adapter_id TEXT DEFAULT 'base',
                task TEXT DEFAULT '',
                gpu_hours REAL DEFAULT 0.0,
                gpu_type TEXT DEFAULT 'unknown',
                cost_usd REAL DEFAULT 0.0,
                benchmark_delta REAL DEFAULT 0.0,
                ran_at TEXT NOT NULL
            )
        """)

    def record(self, adapter_id: str, task: str, gpu_hours: float,
               gpu_type: str = "unknown", benchmark_delta: float = 0.0,
               cost_per_hour: float = GPU_COST_PER_HOUR) -> str:
        rid = str(uuid.uuid4())
        self.db.execute(
            """INSERT INTO gpu_runs
               (id, adapter_id, task, gpu_hours, gpu_type, cost_usd, benchmark_delta, ran_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, adapter_id, task, gpu_hours, gpu_type,
             round(gpu_hours * cost_per_hour, 4), benchmark_delta,
             datetime.now(timezone.utc).isoformat()),
        )
        return rid

    def stats(self) -> dict:
        rows = self.db.fetchall("SELECT * FROM gpu_runs")
        total_hours = sum(r.get("gpu_hours", 0) for r in rows)
        total_cost = sum(r.get("cost_usd", 0) for r in rows)
        total_delta = sum(r.get("benchmark_delta", 0) for r in rows)
        per_adapter = {}
        for r in rows:
            a = r["adapter_id"]
            if a not in per_adapter:
                per_adapter[a] = {"runs": 0, "gpu_hours": 0.0, "cost_usd": 0.0,
                                  "benchmark_delta": 0.0}
            per_adapter[a]["runs"] += 1
            per_adapter[a]["gpu_hours"] += r.get("gpu_hours", 0)
            per_adapter[a]["cost_usd"] += r.get("cost_usd", 0)
            per_adapter[a]["benchmark_delta"] += r.get("benchmark_delta", 0)
        for a in per_adapter:
            d = per_adapter[a]
            d["cost_per_point"] = (round(d["cost_usd"] / d["benchmark_delta"], 4)
                                   if d["benchmark_delta"] else None)
        return {
            "total_runs": len(rows),
            "total_gpu_hours": round(total_hours, 2),
            "total_cost_usd": round(total_cost, 2),
            "total_benchmark_delta": round(total_delta, 4),
            "cost_per_benchmark_point": (round(total_cost / total_delta, 4) if total_delta else None),
            "per_adapter": per_adapter,
        }

    def history(self, limit: int = 50) -> List[dict]:
        return self.db.fetchall("SELECT * FROM gpu_runs ORDER BY ran_at DESC LIMIT ?", (limit,))


class AlertEngine:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT DEFAULT '',
                event_type TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                webhook_sent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

    def notify(self, severity: str, title: str, message: str = "",
               event_type: str = "", payload: dict = None,
               webhook_url: str = "") -> str:
        aid = str(uuid.uuid4())
        webhook_sent = 0
        if webhook_url:
            webhook_sent = int(self._send_webhook(webhook_url, title, message, payload))
        self.db.execute(
            """INSERT INTO alerts
               (id, severity, title, message, event_type, payload, webhook_sent, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (aid, severity, title, message, event_type, str(payload or {}),
             webhook_sent, datetime.now(timezone.utc).isoformat()),
        )
        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                EventType.ALERT_TRIGGERED, "alert_engine",
                payload={"severity": severity, "title": title, "alert_id": aid},
                priority=EventPriority.HIGH if severity in ("critical", "high") else EventPriority.MEDIUM,
            ))
        except RuntimeError:
            pass
        logger.info("alert_triggered", severity=severity, title=title)
        return aid

    def _send_webhook(self, url: str, title: str, message: str, payload: dict) -> bool:
        try:
            import urllib.request
            body = json.dumps({"title": title, "message": message, "data": payload or {}}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    def list_alerts(self, limit: int = 50) -> List[dict]:
        return self.db.fetchall("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))


class LearningProfiler:
    STACK_KEYWORDS = {
        "python": ["python", "fastapi", "django", "pandas", "pytest"],
        "javascript": ["javascript", "react", "next.js", "typescript", "node"],
        "devops": ["docker", "kubernetes", "ci/cd", "terraform", "nginx"],
        "ml": ["pytorch", "lora", "fine-tuning", "inference", "tensor"],
        "security": ["security", "cve", "oauth", "jwt", "penetration"],
        "databases": ["sql", "postgres", "redis", "duckdb", "indexing"],
    }

    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS profile_signals (
                id TEXT PRIMARY KEY,
                stack TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                last_seen TEXT NOT NULL
            )
        """)

    def observe(self, text: str, weight: float = 1.0):
        lower = text.lower()
        hits = {stack: sum(1 for k in kws if k in lower)
                for stack, kws in self.STACK_KEYWORDS.items()}
        for stack, count in hits.items():
            if count == 0:
                continue
            existing = self.db.fetchone(
                "SELECT id, weight FROM profile_signals WHERE stack = ?", (stack,)
            )
            add = min(1.0, count * 0.2) * weight
            if existing:
                self.db.execute(
                    "UPDATE profile_signals SET weight = weight + ?, last_seen = ? WHERE id = ?",
                    (add, datetime.now(timezone.utc).isoformat(), existing["id"]),
                )
            else:
                self.db.execute(
                    """INSERT INTO profile_signals (id, stack, weight, last_seen)
                       VALUES (?, ?, ?, ?)""",
                    (str(uuid.uuid4()), stack, add, datetime.now(timezone.utc).isoformat()),
                )

    def profile(self) -> dict:
        rows = self.db.fetchall("SELECT * FROM profile_signals ORDER BY weight DESC")
        total = sum(r["weight"] for r in rows) or 1.0
        stacks = [{"stack": r["stack"], "weight": r["weight"],
                   "share": round(r["weight"] / total, 3), "last_seen": r["last_seen"]}
                  for r in rows]
        dominant = stacks[0]["stack"] if stacks else "general"
        return {
            "dominant_stack": dominant,
            "stacks": stacks,
            "sample_count": len(rows),
        }

import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Callable, Coroutine, Any, Dict, List
from .database.sqlite import SQLiteStore
from .eventbus.bus import get_bus, EventBus
from .eventbus.models import EventType, EventPriority

logger = structlog.get_logger()


class PipelineScheduler:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.bus = get_bus()
        self._tasks: Dict[str, Dict] = {}
        self._running = False
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                pipeline_name TEXT NOT NULL,
                schedule_type TEXT NOT NULL DEFAULT 'interval',
                interval_minutes INTEGER DEFAULT 0,
                cron_expression TEXT,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                config TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_log (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                pipeline_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT DEFAULT '{}',
                error TEXT
            )
        """)

    def register_job(self, name: str, pipeline_name: str, interval_minutes: int = 0,
                      cron_expression: str = None, config: dict = None) -> str:
        import uuid
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """INSERT OR REPLACE INTO scheduler_jobs
               (id, name, pipeline_name, schedule_type, interval_minutes, cron_expression,
                enabled, config, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (job_id, name, pipeline_name,
             "cron" if cron_expression else "interval",
             interval_minutes, cron_expression or "",
             str(config or {}), now),
        )
        self._tasks[job_id] = {
            "name": name,
            "pipeline_name": pipeline_name,
            "interval_minutes": interval_minutes,
            "cron_expression": cron_expression,
            "enabled": True,
            "config": config or {},
        }
        logger.info("scheduler_job_registered", name=name, pipeline=pipeline_name)
        return job_id

    async def start(self):
        self._running = True
        logger.info("pipeline_scheduler_started")
        while self._running:
            await asyncio.sleep(60)
            await self._check_and_run()

    async def stop(self):
        self._running = False
        logger.info("pipeline_scheduler_stopped")

    async def _check_and_run(self):
        now = datetime.now(timezone.utc)
        rows = self.db.fetchall(
            "SELECT * FROM scheduler_jobs WHERE enabled = 1"
        )
        for row in rows:
            if not self._running:
                break
            should_run = False
            if row["schedule_type"] == "interval" and row["interval_minutes"] > 0:
                last_run = row.get("last_run")
                if not last_run:
                    should_run = True
                else:
                    try:
                        last_dt = datetime.fromisoformat(last_run)
                        elapsed = (now - last_dt).total_seconds() / 60
                        should_run = elapsed >= row["interval_minutes"]
                    except Exception:
                        should_run = True

            if not should_run:
                continue

            from ..agents.router import get_orchestrator
            try:
                orch = get_orchestrator()
                results = await orch.run_pipeline(row["pipeline_name"])
                status = "completed"
                result_summary = {"steps": len(results), "status": status}
                self._log_run(row["id"], row["pipeline_name"], status, result_summary)

                self.db.execute(
                    "UPDATE scheduler_jobs SET last_run = ?, next_run = ? WHERE id = ?",
                    (now.isoformat(),
                     (datetime.fromtimestamp(now.timestamp() + row["interval_minutes"] * 60)).isoformat() if row["interval_minutes"] > 0 else "",
                     row["id"]),
                )
                logger.info("scheduled_pipeline_completed", name=row["name"], pipeline=row["pipeline_name"])

            except Exception as e:
                self._log_run(row["id"], row["pipeline_name"], "failed", {"error": str(e)})
                logger.error("scheduled_pipeline_failed", name=row["name"], error=str(e))

    def _log_run(self, job_id: str, pipeline: str, status: str, result: dict):
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        existing = self.db.fetchone(
            "SELECT id FROM scheduler_log WHERE job_id = ? AND started_at LIKE ?",
            (job_id, now[:16] + "%"),
        )
        if existing:
            self.db.execute(
                "UPDATE scheduler_log SET status = ?, completed_at = ?, result = ? WHERE id = ?",
                (status, now, str(result), existing["id"]),
            )
        else:
            self.db.execute(
                """INSERT INTO scheduler_log
                   (id, job_id, pipeline_name, status, started_at, completed_at, result)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), job_id, pipeline, status, now, now if status == "completed" else "", str(result)),
            )

    def get_jobs(self) -> List[dict]:
        rows = self.db.fetchall("SELECT * FROM scheduler_jobs ORDER BY created_at DESC")
        for r in rows:
            r["config"] = eval(r.get("config", "{}"))
        return rows

    def get_logs(self, limit: int = 50) -> List[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM scheduler_log ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        for r in rows:
            r["result"] = eval(r.get("result", "{}"))
        return rows

    def enable_job(self, job_id: str, enabled: bool) -> bool:
        self.db.execute(
            "UPDATE scheduler_jobs SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, job_id),
        )
        return True

    def register_default_jobs(self, orch=None):
        # NOTE: if orch is provided, the caller manages the orchestrator lifecycle.
        # Default jobs just define schedules; execution uses the orchestrator
        # resolved at run time via get_orchestrator().
        self.register_job(
            name="daily-research",
            pipeline_name="daily-research",
            interval_minutes=1440,
            config={"description": "Daily crawl, extract, govern, and score new knowledge"},
        )
        self.register_job(
            name="full-auto-weekly",
            pipeline_name="full-auto",
            interval_minutes=10080,
            config={"description": "Weekly full auto pipeline — research through planning"},
        )
        self.register_job(
            name="doc-check-hourly",
            pipeline_name="daily-research",
            interval_minutes=60,
            config={"description": "Hourly check for new releases and docs changes"},
        )
        logger.info("default_scheduler_jobs_registered")
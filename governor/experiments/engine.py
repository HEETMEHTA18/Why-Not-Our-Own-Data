import uuid
from datetime import datetime, timezone
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from .models import ExperimentConfig, ExperimentRun, ExperimentStatus, ExperimentReport


EXPERIMENT_DEFINITIONS = [
    {
        "name": "quality-threshold-benchmark",
        "description": "Measure how dataset quality threshold affects model performance on coding benchmarks",
        "hypothesis": "Datasets filtered at quality >= 0.85 produce better models than unfiltered datasets 3x the size",
        "methodology": "1. Collect all dataset examples. 2. Filter at thresholds [0.0, 0.5, 0.7, 0.85, 0.95]. 3. Train LoRA adapter at each threshold. 4. Evaluate on HumanEval and MBPP. 5. Compare pass@1 scores.",
        "metrics": ["pass@1", "training_loss", "eval_loss", "dataset_size"],
        "parameters": {"thresholds": [0.0, 0.5, 0.7, 0.85, 0.95], "base_model": "codellama-7b", "lora_rank": 16},
    },
    {
        "name": "knowledge-source-comparison",
        "description": "Compare model improvement from different knowledge sources (crawled vs user corrections vs both)",
        "hypothesis": "Combined crawled + user correction knowledge produces 20% better results than either source alone",
        "methodology": "1. Create 3 datasets: crawled-only, correction-only, combined. 2. Match sizes to control for quantity. 3. Train adapters. 4. Evaluate on zero-shot coding tasks. 5. Evaluate on user-specific tasks.",
        "metrics": ["pass@1", "user_satisfaction", "knowledge_coverage", "hallucination_rate"],
        "parameters": {"base_model": "codellama-7b", "epochs": 3, "lr": 2e-4},
    },
    {
        "name": "forgetting-replay-ratio",
        "description": "Determine optimal replay buffer ratio to prevent catastrophic forgetting during continual learning",
        "hypothesis": "A 20% replay buffer prevents >95% of forgetting while allowing 80%+ new knowledge absorption",
        "methodology": "1. Benchmark base model on 5 tasks. 2. Train on new knowledge only. 3. Train with 5%, 10%, 20%, 50% replay. 4. Measure old task performance retention. 5. Measure new task accuracy.",
        "metrics": ["old_task_accuracy", "new_task_accuracy", "forgetting_rate", "training_time"],
        "parameters": {"replay_ratios": [0.0, 0.05, 0.1, 0.2, 0.5], "base_model": "codellama-7b", "lora_rank": 16},
    },
    {
        "name": "classifier-accuracy-evaluation",
        "description": "Evaluate the knowledge type classifier accuracy against human-labeled ground truth",
        "hypothesis": "Regex-based classifier achieves >70% accuracy on major categories (security, bug_fix, api_update)",
        "methodology": "1. Sample 200 crawled items. 2. Label by human (simulated). 3. Run classifier. 4. Compute precision, recall, F1 per category. 5. Identify weakest categories.",
        "metrics": ["precision", "recall", "f1_score", "accuracy", "coverage"],
        "parameters": {"sample_size": 200, "categories": 12},
    },
    {
        "name": "knowledge-importance-scoring",
        "description": "Validate that importance scores correlate with actual user-flagged useful knowledge",
        "hypothesis": "Items with importance > 0.7 are 4x more likely to be used in user conversations",
        "methodology": "1. Score all extracted knowledge. 2. Track which items are referenced in user conversations over 30 days. 3. Compute correlation between importance score and usage. 4. Refine scoring weights.",
        "metrics": ["correlation", "usage_rate_low_importance", "usage_rate_high_importance", "lift"],
        "parameters": {"duration_days": 30, "importance_bins": 5},
    },
]


class ExperimentEngine:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_table()

    def _init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS experiment_configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                hypothesis TEXT,
                methodology TEXT,
                metrics TEXT DEFAULT '[]',
                parameters TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                run_number INTEGER DEFAULT 1,
                status TEXT DEFAULT 'designed',
                parameters TEXT DEFAULT '{}',
                results TEXT DEFAULT '{}',
                metrics TEXT DEFAULT '{}',
                duration_seconds REAL,
                error TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiment_configs(id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS experiment_reports (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                findings TEXT,
                conclusion TEXT,
                recommendations TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiment_configs(id)
            )
        """)

    def seed_experiments(self) -> int:
        existing = self.db.fetchone("SELECT COUNT(*) as c FROM experiment_configs")["c"]
        if existing > 0:
            return 0
        count = 0
        for edef in EXPERIMENT_DEFINITIONS:
            config = ExperimentConfig(
                id=str(uuid.uuid4()),
                **edef,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._save_config(config)
            count += 1
        return count

    def _save_config(self, config: ExperimentConfig):
        self.db.execute(
            """INSERT OR REPLACE INTO experiment_configs
               (id, name, description, hypothesis, methodology, metrics, parameters, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (config.id, config.name, config.description, config.hypothesis,
             config.methodology, str(config.metrics), str(config.parameters), config.created_at),
        )

    def list_experiments(self) -> List[dict]:
        rows = self.db.fetchall("SELECT * FROM experiment_configs ORDER BY created_at DESC")
        for r in rows:
            r["metrics"] = eval(r.get("metrics", "[]"))
            r["parameters"] = eval(r.get("parameters", "{}"))
        return rows

    def get_experiment(self, experiment_id: str) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM experiment_configs WHERE id = ?", (experiment_id,))
        if not row:
            return None
        row["metrics"] = eval(row.get("metrics", "[]"))
        row["parameters"] = eval(row.get("parameters", "{}"))
        return row

    def get_experiment_by_name(self, name: str) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM experiment_configs WHERE name = ?", (name,))
        if not row:
            return None
        row["metrics"] = eval(row.get("metrics", "[]"))
        row["parameters"] = eval(row.get("parameters", "{}"))
        return row

    def create_run(self, experiment_id: str, parameters: dict = None) -> ExperimentRun:
        run_count = self.db.fetchone(
            "SELECT COUNT(*) as c FROM experiment_runs WHERE experiment_id = ?", (experiment_id,)
        )["c"]
        run = ExperimentRun(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            run_number=run_count + 1,
            status=ExperimentStatus.DESIGNED,
            parameters=parameters or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_run(run)
        return run

    def _save_run(self, run: ExperimentRun):
        self.db.execute(
            """INSERT OR REPLACE INTO experiment_runs
               (id, experiment_id, run_number, status, parameters, results, metrics, duration_seconds, error, started_at, completed_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run.id, run.experiment_id, run.run_number, run.status.value,
             str(run.parameters), str(run.results), str(run.metrics),
             run.duration_seconds, run.error, run.started_at, run.completed_at, run.created_at),
        )

    def update_run(self, run_id: str, **kwargs) -> bool:
        fields = []
        values = []
        for k, v in kwargs.items():
            if k in ("results", "metrics", "parameters"):
                fields.append(f"{k} = ?")
                values.append(str(v))
            elif k == "status":
                fields.append("status = ?")
                values.append(v.value if isinstance(v, ExperimentStatus) else v)
            elif k in ("duration_seconds", "error", "started_at", "completed_at"):
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return False
        values.append(run_id)
        self.db.execute(
            f"UPDATE experiment_runs SET {', '.join(fields)} WHERE id = ?", tuple(values)
        )
        return True

    def list_runs(self, experiment_id: str) -> List[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM experiment_runs WHERE experiment_id = ? ORDER BY run_number DESC", (experiment_id,)
        )
        for r in rows:
            r["parameters"] = eval(r.get("parameters", "{}"))
            r["results"] = eval(r.get("results", "{}"))
            r["metrics"] = eval(r.get("metrics", "{}"))
        return rows

    def create_report(self, experiment_id: str, summary: str, findings: str,
                      conclusion: str, recommendations: List[str] = None) -> ExperimentReport:
        report = ExperimentReport(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            summary=summary,
            findings=findings,
            conclusion=conclusion,
            recommendations=recommendations or [],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.execute(
            """INSERT OR REPLACE INTO experiment_reports
               (id, experiment_id, summary, findings, conclusion, recommendations, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (report.id, report.experiment_id, report.summary, report.findings,
             report.conclusion, str(report.recommendations), report.created_at),
        )
        return report

    def list_reports(self, experiment_id: Optional[str] = None) -> List[dict]:
        if experiment_id:
            rows = self.db.fetchall(
                "SELECT * FROM experiment_reports WHERE experiment_id = ? ORDER BY created_at DESC", (experiment_id,)
            )
        else:
            rows = self.db.fetchall("SELECT * FROM experiment_reports ORDER BY created_at DESC")
        for r in rows:
            r["recommendations"] = eval(r.get("recommendations", "[]"))
        return rows

    def stats(self) -> dict:
        configs = self.db.fetchone("SELECT COUNT(*) as c FROM experiment_configs")["c"]
        runs = self.db.fetchone("SELECT COUNT(*) as c FROM experiment_runs")["c"]
        reports = self.db.fetchone("SELECT COUNT(*) as c FROM experiment_reports")["c"]
        by_status = self.db.fetchall(
            "SELECT status, COUNT(*) as cnt FROM experiment_runs GROUP BY status"
        )
        return {
            "total_experiments": configs,
            "total_runs": runs,
            "total_reports": reports,
            "runs_by_status": {r["status"]: r["cnt"] for r in by_status},
        }

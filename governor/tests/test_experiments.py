import pytest
from ..experiments.engine import ExperimentEngine
from ..experiments.models import ExperimentStatus


@pytest.fixture
def engine():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return ExperimentEngine(db=db)


class TestExperimentEngine:
    def test_init_creates_tables(self, engine):
        for table in ["experiment_configs", "experiment_runs", "experiment_reports"]:
            row = engine.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            assert row is not None, f"Table {table} not created"

    def test_seed_experiments(self, engine):
        count = engine.seed_experiments()
        assert count == len([
            "quality-threshold-benchmark",
            "knowledge-source-comparison",
            "forgetting-replay-ratio",
            "classifier-accuracy-evaluation",
            "knowledge-importance-scoring",
        ])
        count2 = engine.seed_experiments()
        assert count2 == 0

    def test_list_experiments(self, engine):
        engine.seed_experiments()
        experiments = engine.list_experiments()
        assert len(experiments) >= 5
        names = [e["name"] for e in experiments]
        assert "quality-threshold-benchmark" in names

    def test_get_experiment(self, engine):
        engine.seed_experiments()
        experiments = engine.list_experiments()
        exp = engine.get_experiment(experiments[0]["id"])
        assert exp is not None
        assert exp["id"] == experiments[0]["id"]

    def test_get_experiment_by_name(self, engine):
        engine.seed_experiments()
        exp = engine.get_experiment_by_name("quality-threshold-benchmark")
        assert exp is not None
        assert exp["name"] == "quality-threshold-benchmark"

    def test_create_run(self, engine):
        engine.seed_experiments()
        exp = engine.get_experiment_by_name("quality-threshold-benchmark")
        params = {"threshold": 0.85, "epochs": 3}
        run = engine.create_run(exp["id"], parameters=params)
        assert run.run_number == 1
        assert run.status == ExperimentStatus.DESIGNED

    def test_multiple_runs(self, engine):
        engine.seed_experiments()
        exp = engine.get_experiment_by_name("quality-threshold-benchmark")
        engine.create_run(exp["id"])
        run2 = engine.create_run(exp["id"])
        assert run2.run_number == 2

    def test_update_run(self, engine):
        engine.seed_experiments()
        exp = engine.get_experiment_by_name("quality-threshold-benchmark")
        run = engine.create_run(exp["id"])
        success = engine.update_run(
            run.id,
            status=ExperimentStatus.COMPLETED,
            results={"pass@1": 0.45},
            duration_seconds=3600,
        )
        assert success
        runs = engine.list_runs(exp["id"])
        assert runs[0]["status"] == "completed"
        assert runs[0]["duration_seconds"] == 3600

    def test_create_report(self, engine):
        engine.seed_experiments()
        exp = engine.get_experiment_by_name("quality-threshold-benchmark")
        report = engine.create_report(
            experiment_id=exp["id"],
            summary="Quality threshold of 0.85 provides best trade-off",
            findings="Higher thresholds reduce dataset size too much",
            conclusion="Use 0.85 as default quality threshold",
            recommendations=["Monitor threshold over time", "Re-evaluate quarterly"],
        )
        assert report.summary.startswith("Quality threshold")

    def test_stats(self, engine):
        engine.seed_experiments()
        stats = engine.stats()
        assert stats["total_experiments"] >= 5
        assert stats["total_runs"] == 0
        assert stats["total_reports"] == 0

import pytest
from ..database.sqlite import SQLiteStore
from ..governor.engine import TrainingGovernor
from ..governor.conditions import ConditionChecker
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate
from ..dataset.builder import DatasetBuilder


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


@pytest.fixture
def populated_db(db):
    collector = CollectorStorage(db)
    builder = DatasetBuilder(db)
    for i in range(60):
        conv = collector.store_conversation(
            ConversationCreate(
                session_id="s1", prompt=f"How do I optimize database query {i}?", response=f"Answer {i}",
                rating=5,
            )
        )
        collector.apply_correction(CorrectionCreate(
            conversation_id=conv.id,
            corrected_response=f"To optimize query {i}, use proper indexing and avoid SELECT *. First analyze the query plan using EXPLAIN. Add composite indexes on WHERE and JOIN columns. Consider query caching for frequently accessed data. This is an important optimization technique that reduces latency and improves throughput significantly. Use asynchronous processing for concurrent queries.",
        ))
    builder.build_from_corrections()
    scorer = __import__("governor.quality.scorer", fromlist=["QualityScorer"]).QualityScorer(db)
    scorer.score_all()
    return db


class TestConditionChecker:
    def test_example_count(self, db):
        checker = ConditionChecker(db)
        result = checker._check_example_count()
        assert result["count"] == 0
        assert result["passed"] is False

    def test_check_all_empty(self, db):
        checker = ConditionChecker(db)
        results = checker.check_all()
        assert all(not v["passed"] for v in results.values())


class TestTrainingGovernor:
    def test_evaluate_not_ready(self, db):
        governor = TrainingGovernor(db)
        decision = governor.evaluate()
        assert decision.recommend is False

    def test_evaluate_ready(self, populated_db):
        governor = TrainingGovernor(populated_db)
        decision = governor.evaluate()
        assert decision.recommend is True
        assert decision.recommendation_id is not None

    def test_approve_reject(self, populated_db):
        governor = TrainingGovernor(populated_db)
        decision = governor.evaluate()
        rec_id = decision.recommendation_id

        approved = governor.approve(rec_id, "Looks good")
        assert approved.status == "approved"
        assert approved.approved_at is not None

    def test_list_recommendations(self, populated_db):
        governor = TrainingGovernor(populated_db)
        governor.evaluate()
        recs = governor.list_recommendations()
        assert len(recs) >= 1

import pytest
from ..database.sqlite import SQLiteStore
from ..consent.manager import ConsentManager
from ..consent.models import ConsentResponse
from ..governor.engine import TrainingGovernor
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate
from ..dataset.builder import DatasetBuilder


@pytest.fixture
def ready_db():
    db = SQLiteStore(db_path=":memory:")
    collector = CollectorStorage(db)
    builder = DatasetBuilder(db)
    for i in range(60):
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt=f"How do I optimize query {i}?", response=f"A{i}", rating=5)
        )
        collector.apply_correction(CorrectionCreate(
            conversation_id=conv.id, corrected_response=f"To optimize query {i}, use proper indexing and avoid SELECT *. Analyze the query plan, add composite indexes on WHERE and JOIN columns, and consider caching for frequently accessed data. This approach reduces latency and improves throughput significantly.",
        ))
    builder.build_from_corrections()
    scorer = __import__("governor.quality.scorer", fromlist=["QualityScorer"]).QualityScorer(db)
    scorer.score_all()
    return db


class TestConsentManager:
    def test_build_prompt(self, ready_db):
        governor = TrainingGovernor(ready_db)
        decision = governor.evaluate()
        manager = ConsentManager(ready_db)
        prompt = manager.build_prompt(decision.recommendation_id)
        assert prompt is not None
        assert prompt.corrections_count >= 50
        assert prompt.estimated_improvement > 0

    def test_approve_decision(self, ready_db):
        governor = TrainingGovernor(ready_db)
        decision = governor.evaluate()
        manager = ConsentManager(ready_db)
        result = manager.record_decision(ConsentResponse(
            recommendation_id=decision.recommendation_id,
            decision="yes",
            timestamp="2024-01-01T00:00:00",
        ))
        assert result is True
        rec = governor.get_recommendation(decision.recommendation_id)
        assert rec.status == "approved"

    def test_reject_decision(self, ready_db):
        governor = TrainingGovernor(ready_db)
        decision = governor.evaluate()
        manager = ConsentManager(ready_db)
        result = manager.record_decision(ConsentResponse(
            recommendation_id=decision.recommendation_id,
            decision="no",
            timestamp="2024-01-01T00:00:00",
        ))
        assert result is False
        rec = governor.get_recommendation(decision.recommendation_id)
        assert rec.status == "rejected"

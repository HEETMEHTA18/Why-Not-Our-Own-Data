import pytest
from ..database.sqlite import SQLiteStore
from ..quality.scorer import QualityScorer
from ..quality.metrics import QualityMetrics
from ..quality.models import QualityScore
from ..dataset.builder import DatasetBuilder
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


class TestQualityScorer:
    def test_score_example(self, db):
        collector = CollectorStorage(db)
        builder = DatasetBuilder(db)
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt="Explain Docker", response="Docker is...", rating=5)
        )
        collector.apply_correction(CorrectionCreate(
            conversation_id=conv.id,
            corrected_response="Docker is a container platform that... (detailed explanation)",
        ))
        examples = builder.build_from_corrections()
        scorer = QualityScorer(db)
        score = scorer.score_example(examples[0])
        assert score.overall > 0
        assert score.coherence > 0
        assert score.correctness > 0

    def test_score_all(self, db):
        collector = CollectorStorage(db)
        builder = DatasetBuilder(db)
        for i in range(3):
            conv = collector.store_conversation(
                ConversationCreate(session_id="s1", prompt=f"Q{i}", response=f"A{i}", rating=5)
            )
            collector.apply_correction(CorrectionCreate(
                conversation_id=conv.id, corrected_response=f"Answer {i} with details..."
            ))
        builder.build_from_corrections()
        scorer = QualityScorer(db)
        scores = scorer.score_all()
        assert len(scores) == 3


class TestQualityMetrics:
    def test_distribution(self):
        scores = [
            QualityScore(id="1", example_id="e1", overall=0.1, scored_at="now"),
            QualityScore(id="2", example_id="e2", overall=0.5, scored_at="now"),
            QualityScore(id="3", example_id="e3", overall=0.9, scored_at="now"),
        ]
        dist = QualityMetrics.distribution(scores)
        assert dist["0.0-0.2"] == 1
        assert dist["0.4-0.6"] == 1
        assert dist["0.8-1.0"] == 1

    def test_report(self):
        scores = [
            QualityScore(id="1", example_id="e1", overall=0.8, scored_at="now"),
            QualityScore(id="2", example_id="e2", overall=0.9, scored_at="now"),
        ]
        report = QualityMetrics.report(scores)
        assert report["total_scored"] == 2
        assert report["mean_overall"] == 0.85

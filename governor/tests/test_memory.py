import pytest
from ..database.sqlite import SQLiteStore
from ..memory.classifier import MemoryClassifier
from ..memory.models import MemoryClass
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


class TestMemoryClassifier:
    def test_classify_low_value(self, db):
        collector = CollectorStorage(db)
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt="Hi", response="Hello", rating=1)
        )
        classifier = MemoryClassifier(db)
        result = classifier.classify(conv.id)
        assert result.classification == MemoryClass.IGNORED

    def test_classify_training_value(self, db):
        collector = CollectorStorage(db)
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt="What is ML?", response="Machine learning", rating=3)
        )
        collector.apply_correction(CorrectionCreate(
            conversation_id=conv.id,
            corrected_response="Machine Learning is a field of AI...",
        ))
        classifier = MemoryClassifier(db)
        result = classifier.classify(conv.id)
        assert result.classification == MemoryClass.TRAINING_DATA

    def test_stats(self, db):
        collector = CollectorStorage(db)
        for i in range(3):
            conv = collector.store_conversation(
                ConversationCreate(session_id="s1", prompt=f"Q{i}", response=f"A{i}", rating=0)
            )
            classifier = MemoryClassifier(db)
            classifier.classify(conv.id)
        stats = classifier.stats()
        assert sum(stats.values()) == 3

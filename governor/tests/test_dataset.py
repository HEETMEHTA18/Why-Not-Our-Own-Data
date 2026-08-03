import pytest
from ..database.sqlite import SQLiteStore
from ..dataset.builder import DatasetBuilder
from ..dataset.cleaner import DatasetCleaner
from ..dataset.validator import DatasetValidator
from ..dataset.models import InstructionExample
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


@pytest.fixture
def collector(db):
    return CollectorStorage(db)


@pytest.fixture
def builder(db):
    return DatasetBuilder(db)


class TestDatasetBuilder:
    def test_build_from_corrections(self, collector, builder):
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt="What is Python?", response="A language")
        )
        collector.apply_correction(CorrectionCreate(
            conversation_id=conv.id, corrected_response="Python is a programming language."
        ))
        examples = builder.build_from_corrections()
        assert len(examples) == 1
        assert examples[0].instruction == "What is Python?"
        assert examples[0].output == "Python is a programming language."

    def test_export_alpaca(self, collector, builder):
        conv = collector.store_conversation(
            ConversationCreate(session_id="s1", prompt="Hi", response="Hello", rating=5)
        )
        examples = builder.build_from_ratings(min_rating=4)
        export = builder.export_alpaca()
        assert len(export) == 1
        assert export[0]["instruction"] == "Hi"


class TestDatasetCleaner:
    def test_find_duplicates(self):
        examples = [
            InstructionExample(id="1", conversation_id="c1", instruction="Hello", output="Hi", created_at="now"),
            InstructionExample(id="2", conversation_id="c2", instruction="Hello", output="Hi", created_at="now"),
            InstructionExample(id="3", conversation_id="c3", instruction="What", output="Nothing", created_at="now"),
        ]
        cleaner = DatasetCleaner()
        dups = cleaner.find_duplicates(examples)
        assert len(dups) == 1
        assert dups[0][0] == "2"

    def test_remove_spam(self):
        examples = [
            InstructionExample(id="1", conversation_id="c1", instruction="Bad", output="I cannot assist with that", created_at="now"),
            InstructionExample(id="2", conversation_id="c2", instruction="Good", output="Here is the answer...", created_at="now"),
        ]
        cleaner = DatasetCleaner()
        cleaned = cleaner.remove_spam(examples)
        assert len(cleaned) == 1
        assert cleaned[0].id == "2"

    def test_find_contradictions(self):
        examples = [
            InstructionExample(id="1", conversation_id="c1", instruction="What is 2+2?", output="4", created_at="now"),
            InstructionExample(id="2", conversation_id="c2", instruction="What is 2+2?", output="5", created_at="now"),
        ]
        cleaner = DatasetCleaner()
        contradictions = cleaner.find_contradictions(examples)
        assert len(contradictions) == 1


class TestDatasetValidator:
    def test_validate(self):
        examples = [
            InstructionExample(id="1", conversation_id="c1", instruction="Hi", output="Hello World", created_at="now"),
            InstructionExample(id="2", conversation_id="c2", instruction="", output="", created_at="now"),
        ]
        validator = DatasetValidator()
        errors = validator.validate(examples)
        assert len(errors) == 2

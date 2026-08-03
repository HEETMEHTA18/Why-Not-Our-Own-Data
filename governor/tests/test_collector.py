import pytest
from ..database.sqlite import SQLiteStore
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationCreate, CorrectionCreate


@pytest.fixture
def db():
    store = SQLiteStore(db_path=":memory:")
    return store


@pytest.fixture
def storage(db):
    return CollectorStorage(db)


class TestCollector:
    def test_store_and_retrieve(self, storage):
        conv = storage.store_conversation(
            ConversationCreate(session_id="s1", prompt="Hello", response="Hi there", model="llama3")
        )
        assert conv.id is not None
        assert conv.prompt == "Hello"
        assert conv.response == "Hi there"

        fetched = storage.get_conversation(conv.id)
        assert fetched is not None
        assert fetched.prompt == "Hello"

    def test_apply_correction(self, storage):
        conv = storage.store_conversation(
            ConversationCreate(session_id="s1", prompt="Explain ML", response="Machine learning...")
        )
        corrected = storage.apply_correction(CorrectionCreate(
            conversation_id=conv.id, corrected_response="Machine Learning is..."
        ))
        assert corrected is not None
        assert corrected.corrected_response == "Machine Learning is..."

    def test_list_with_filters(self, storage):
        for i in range(5):
            storage.store_conversation(
                ConversationCreate(session_id="s1", prompt=f"Q{i}", response=f"A{i}", rating=i)
            )
        all_convs = storage.list_conversations()
        assert len(all_convs) == 5

        rated = storage.list_conversations(type("F", (), {
            "session_id": None, "min_rating": 3, "has_correction": None,
            "start_date": None, "end_date": None, "limit": 100, "offset": 0
        })())
        assert len(rated) == 2

    def test_count(self, storage):
        assert storage.count() == 0
        storage.store_conversation(ConversationCreate(session_id="s1", prompt="Hi", response="Hello"))
        assert storage.count() == 1

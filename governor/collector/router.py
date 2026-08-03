from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .models import ConversationCreate, CorrectionCreate, Conversation, ConversationFilter
from .storage import CollectorStorage

router = APIRouter(prefix="/collect", tags=["collector"])


def get_storage() -> CollectorStorage:
    return CollectorStorage()


@router.post("/conversation", response_model=Conversation)
def store_conversation(data: ConversationCreate, storage: CollectorStorage = Depends(get_storage)):
    return storage.store_conversation(data)


@router.get("/conversation/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str, storage: CollectorStorage = Depends(get_storage)):
    conv = storage.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/conversations", response_model=List[Conversation])
def list_conversations(
    session_id: str = None,
    min_rating: int = None,
    has_correction: bool = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0,
    storage: CollectorStorage = Depends(get_storage),
):
    f = ConversationFilter(
        session_id=session_id, min_rating=min_rating, has_correction=has_correction,
        start_date=start_date, end_date=end_date, limit=limit, offset=offset,
    )
    return storage.list_conversations(f)


@router.post("/correction", response_model=Conversation)
def apply_correction(data: CorrectionCreate, storage: CollectorStorage = Depends(get_storage)):
    conv = storage.apply_correction(data)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.post("/conversation/{conversation_id}/rate", response_model=Conversation)
def rate_conversation(conversation_id: str, rating: int, storage: CollectorStorage = Depends(get_storage)):
    conv = storage.rate_conversation(conversation_id, rating)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/stats")
def get_stats(storage: CollectorStorage = Depends(get_storage)):
    return {
        "total": storage.count(),
        "with_corrections": storage.count(has_correction=True),
        "without_corrections": storage.count(has_correction=False),
    }

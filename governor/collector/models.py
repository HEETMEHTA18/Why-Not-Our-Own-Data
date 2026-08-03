from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConversationCreate(BaseModel):
    session_id: str
    prompt: str
    response: str
    model: str = ""
    latency_ms: float = 0.0
    rating: int = 0
    metadata: dict = {}


class CorrectionCreate(BaseModel):
    conversation_id: str
    corrected_response: str


class Conversation(BaseModel):
    id: str
    session_id: str
    prompt: str
    response: str
    model: str
    latency_ms: float
    timestamp: str
    rating: int
    corrected_response: Optional[str] = None
    correction_timestamp: Optional[str] = None
    metadata: dict = {}


class ConversationFilter(BaseModel):
    session_id: Optional[str] = None
    min_rating: Optional[int] = None
    has_correction: Optional[bool] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 100
    offset: int = 0

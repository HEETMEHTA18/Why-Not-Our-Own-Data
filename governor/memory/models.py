from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class MemoryClass(str, Enum):
    TEMPORARY_CONTEXT = "temporary_context"
    LONG_TERM_MEMORY = "long_term_memory"
    TRAINING_DATA = "training_data"
    IGNORED = "ignored"


class ClassificationResult(BaseModel):
    conversation_id: str
    classification: MemoryClass
    confidence: float
    reason: str
    should_store: bool = True
    tags: List[str] = []


class MemoryEntry(BaseModel):
    id: str
    conversation_id: str
    content: str
    classification: MemoryClass
    embedding: Optional[List[float]] = None
    metadata: dict = {}

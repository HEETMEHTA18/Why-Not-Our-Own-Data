from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class KnowledgeType(str, Enum):
    API_UPDATE = "api_update"
    CODING_STYLE = "coding_style"
    FRAMEWORK = "framework"
    REASONING = "reasoning"
    BUG_FIX = "bug_fix"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    DEPRECATION = "deprecation"
    BEST_PRACTICE = "best_practice"


class ExtractedKnowledge(BaseModel):
    id: str
    crawled_item_id: str
    knowledge_type: KnowledgeType
    title: str
    instruction: str
    input: str
    output: str
    source_url: str
    confidence: float
    language: Optional[str] = None
    frameworks: List[str] = []
    code_snippets: List[str] = []
    tags: List[str] = []
    created_at: str
    metadata: dict = {}


class ExtractionRequest(BaseModel):
    crawled_item_ids: Optional[List[str]] = None
    limit: int = 10


class ExtractionStats(BaseModel):
    total_extracted: int
    by_type: dict
    by_language: dict

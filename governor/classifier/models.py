from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class KnowledgeCategory(str, Enum):
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


class ClassificationVerdict(BaseModel):
    id: str
    item_id: str
    item_type: str
    category: KnowledgeCategory
    confidence: float
    signals: List[str] = []
    secondary_categories: List[dict] = []
    classified_at: str


class ClassificationRequest(BaseModel):
    text: str
    title: Optional[str] = None
    code_snippets: Optional[List[str]] = None

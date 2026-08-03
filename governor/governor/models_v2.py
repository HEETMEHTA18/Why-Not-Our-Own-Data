from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class GovernanceAction(str, Enum):
    IGNORE = "ignore"
    STORE_RAG = "store_rag"
    STORE_KG = "store_kg"
    RECOMMEND_LORA = "recommend_lora"


class GovernanceFactor(str, Enum):
    NOVELTY = "novelty"
    AUTHORITY = "authority"
    FREQUENCY = "frequency"
    COMPLEXITY = "complexity"
    SPECIFICITY = "specificity"
    SECURITY_RELEVANCE = "security_relevance"
    USER_RELEVANCE = "user_relevance"
    CONTRADICTION_RISK = "contradiction_risk"
    FORGETTING_RISK = "forgetting_risk"
    KNOWLEDGE_TYPE = "knowledge_type"


class KnowledgeItemGovernance(BaseModel):
    knowledge_id: str
    action: GovernanceAction
    confidence: float
    reasoning: str
    factors: dict = {}
    alternative_actions: List[dict] = []
    governed_at: str = ""


class GovernancePolicy(BaseModel):
    name: str
    description: str
    rules: List[dict] = []
    priority: int = 0
    active: bool = True


class TrainingGovernanceSummary(BaseModel):
    recommend: bool
    reason: str
    example_count: int
    avg_quality: float
    estimated_improvement: float
    estimated_duration_min: int
    expected_gain_description: str
    gpu_usage_estimate: str
    breakdown: dict = {}
    recommendation_id: Optional[str] = None
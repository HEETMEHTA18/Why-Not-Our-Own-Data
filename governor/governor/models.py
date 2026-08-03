from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TrainingRecommendation(BaseModel):
    id: str
    recommended_at: str
    status: str = "pending"
    example_count: int = 0
    avg_quality: float = 0.0
    estimated_improvement: float = 0.0
    estimated_duration_min: int = 0
    contradiction_count: int = 0
    duplicate_count: int = 0
    diversity_score: float = 0.0
    days_since_last_training: float = 0.0
    decision_log: dict = {}
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None


class GovernorDecision(BaseModel):
    recommend: bool
    reason: str
    details: dict
    recommendation_id: Optional[str] = None


class ApproveRequest(BaseModel):
    recommendation_id: str
    approved: bool
    notes: str = ""

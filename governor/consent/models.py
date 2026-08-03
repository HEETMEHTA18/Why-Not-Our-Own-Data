from pydantic import BaseModel, Field
from typing import Optional


class ConsentPrompt(BaseModel):
    recommendation_id: str
    title: str = "Training Recommendation"
    corrections_count: int
    estimated_improvement: float
    estimated_duration_min: int
    gpu_usage: str = "High"
    quality_score: float
    dataset_size: int
    message: str = ""


class ConsentResponse(BaseModel):
    recommendation_id: str
    decision: str
    timestamp: str
    notes: str = ""

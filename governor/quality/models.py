from pydantic import BaseModel
from typing import Optional, List


class QualityScore(BaseModel):
    id: str
    example_id: str
    overall: float
    coherence: float = 0.0
    correctness: float = 0.0
    completeness: float = 0.0
    novelty: float = 0.0
    confidence: float = 0.0
    importance: float = 0.0
    consistency: float = 0.0
    difficulty: float = 0.0
    scored_at: str


class ScoredExample(BaseModel):
    example_id: str
    scores: QualityScore


class QualityReport(BaseModel):
    total_scored: int
    mean_overall: float
    distribution: dict
    top_examples: List[dict]

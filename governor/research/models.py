from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class ResearchStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class FeasibilityVerdict(str, Enum):
    FEASIBLE = "feasible"
    PARTIALLY_FEASIBLE = "partially_feasible"
    NOT_FEASIBLE = "not_feasible"
    NEEDS_MORE_DATA = "needs_more_data"


class ResearchTopic(BaseModel):
    id: str
    title: str
    question: str
    hypothesis: str
    methodology: str
    status: ResearchStatus = ResearchStatus.PLANNED
    findings: str = ""
    papers_reviewed: List[str] = []
    created_at: str
    updated_at: str


class PaperSummary(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: int
    url: str
    abstract: str
    key_findings: str
    relevance: float
    tags: List[str] = []
    created_at: str


class FeasibilityStudy(BaseModel):
    id: str
    topic_id: str
    verdict: FeasibilityVerdict
    rationale: str
    risks: List[str] = []
    prerequisites: List[str] = []
    estimated_effort: str = ""
    recommendations: List[str] = []
    created_at: str


class MethodComparison(BaseModel):
    id: str
    topic: str
    methods: List[dict]
    winner: str
    rationale: str
    created_at: str

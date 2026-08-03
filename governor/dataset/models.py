from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class InstructionExample(BaseModel):
    id: str
    conversation_id: str
    instruction: str
    input: str = ""
    output: str
    source: str = "correction"
    created_at: str
    quality_score: float = 0.0
    is_valid: bool = True
    metadata: dict = {}


class DatasetExport(BaseModel):
    examples: List[InstructionExample]
    total: int
    avg_quality: float
    export_format: str = "alpaca"


class DatasetStats(BaseModel):
    total_examples: int
    valid_examples: int
    invalid_examples: int
    avg_quality: float
    source_breakdown: dict
    quality_distribution: dict

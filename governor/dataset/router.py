from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from .builder import DatasetBuilder
from .cleaner import DatasetCleaner
from .validator import DatasetValidator
from .models import InstructionExample

router = APIRouter(prefix="/dataset", tags=["dataset"])


def get_builder() -> DatasetBuilder:
    return DatasetBuilder()


@router.post("/build")
def build_dataset(source: str = "corrections", conversation_ids: Optional[List[str]] = Query(None),
                  builder: DatasetBuilder = Depends(get_builder)):
    if source == "corrections":
        examples = builder.build_from_corrections(conversation_ids)
    elif source == "ratings":
        examples = builder.build_from_ratings()
    else:
        raise HTTPException(400, f"Unknown source: {source}")
    return {"built": len(examples), "examples": [e.model_dump() for e in examples]}


@router.get("/examples", response_model=List[InstructionExample])
def list_examples(valid_only: bool = True, limit: int = 100, offset: int = 0,
                  builder: DatasetBuilder = Depends(get_builder)):
    return builder.list_examples(valid_only=valid_only, limit=limit, offset=offset)


@router.get("/export")
def export_dataset(format: str = "alpaca", builder: DatasetBuilder = Depends(get_builder)):
    if format == "alpaca":
        return {"format": "alpaca", "examples": builder.export_alpaca()}
    raise HTTPException(400, f"Unknown format: {format}")


@router.post("/clean")
def clean_dataset(builder: DatasetBuilder = Depends(get_builder)):
    examples = builder.list_examples(valid_only=False, limit=10000, offset=0)
    cleaner = DatasetCleaner()
    cleaned, report = cleaner.clean(examples)
    validator = DatasetValidator()
    errors = validator.validate(cleaned)
    return {"report": report, "validation_errors": errors, "remaining": len(cleaned)}


@router.get("/stats")
def dataset_stats(builder: DatasetBuilder = Depends(get_builder)):
    return builder.stats()

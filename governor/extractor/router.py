from fastapi import APIRouter, Query
from .models import KnowledgeType
from .engine import ExtractionEngine

router = APIRouter(prefix="/extract", tags=["extractor"])
engine = ExtractionEngine()


@router.post("/run")
async def run_extraction(limit: int = 50):
    items = engine.extract_unextracted(limit=limit)
    return {"extracted": len(items)}


@router.get("/knowledge")
def list_knowledge(knowledge_type: str = None, limit: int = 50, offset: int = 0):
    items = engine.list_knowledge(knowledge_type=knowledge_type, limit=limit, offset=offset)
    return {"total": len(items), "items": items}


@router.get("/stats")
def get_stats():
    return engine.stats()


@router.get("/types")
def get_types():
    return {"types": [t.value for t in KnowledgeType]}


@router.post("/push-to-dataset/{knowledge_id}")
def push_to_dataset(knowledge_id: str):
    success = engine.push_to_dataset(knowledge_id)
    return {"success": success}


@router.post("/push-all-to-dataset")
def push_all_to_dataset(knowledge_type: str = None, min_confidence: float = 0.6):
    items = engine.list_knowledge(knowledge_type=knowledge_type, limit=1000, offset=0)
    pushed = 0
    for item in items:
        if item["confidence"] >= min_confidence and not item.get("in_dataset"):
            if engine.push_to_dataset(item["id"]):
                pushed += 1
    return {"pushed": pushed, "total_candidates": len(items)}

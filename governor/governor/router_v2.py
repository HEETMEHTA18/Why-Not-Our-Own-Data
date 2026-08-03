from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .governor_v2 import KnowledgeGovernor
from .engine import TrainingGovernor
from ..database.sqlite import SQLiteStore

router = APIRouter(prefix="/governor", tags=["governor"])

_gov: Optional[KnowledgeGovernor] = None


def get_gov() -> KnowledgeGovernor:
    global _gov
    if _gov is None:
        _gov = KnowledgeGovernor()
    return _gov


class GovernItemRequest(BaseModel):
    knowledge_id: str
    text: str
    title: str = ""
    knowledge_type: str = "unknown"
    confidence: float = 0.0
    metadata: dict = {}


class GovernBatchRequest(BaseModel):
    items: List[GovernItemRequest]


class ApproveRequest(BaseModel):
    recommendation_id: str
    approved: bool
    notes: str = ""


@router.post("/govern")
def govern_item(req: GovernItemRequest):
    gov = get_gov()
    result = gov.govern_knowledge_item(
        knowledge_id=req.knowledge_id,
        text=req.text,
        title=req.title,
        knowledge_type=req.knowledge_type,
        confidence=req.confidence,
        metadata=req.metadata,
    )
    return result.model_dump()


@router.post("/govern/batch")
def govern_batch(req: GovernBatchRequest):
    gov = get_gov()
    items = [i.model_dump() for i in req.items]
    results = gov.govern_batch(items)
    return {"governed": len(results), "items": [r.model_dump() for r in results]}


@router.get("/readiness")
def training_readiness():
    gov = get_gov()
    summary = gov.evaluate_training_readiness()
    return summary.model_dump()


@router.get("/stats")
def governance_stats():
    gov = get_gov()
    return gov.get_governance_stats()


@router.get("/log")
def governance_log(limit: int = 50):
    gov = get_gov()
    rows = gov.db.fetchall(
        "SELECT * FROM knowledge_governance_log ORDER BY governed_at DESC LIMIT ?", (limit,)
    )
    for r in rows:
        r["factors"] = eval(r.get("factors", "{}"))
        r["alternative_actions"] = eval(r.get("alternative_actions", "[]"))
    return {"items": rows}


@router.post("/mark-applied")
def mark_applied(knowledge_ids: List[str]):
    gov = get_gov()
    gov.mark_applied(knowledge_ids)
    return {"applied": len(knowledge_ids)}


@router.get("/policies")
def list_policies():
    gov = get_gov()
    return {"policies": [p.model_dump() for p in gov.policies]}


@router.post("/evaluate")
def evaluate_training():
    tgov = TrainingGovernor()
    decision = tgov.evaluate()
    return decision.model_dump()


@router.post("/approve")
def approve_recommendation(req: ApproveRequest):
    tgov = TrainingGovernor()
    if req.approved:
        result = tgov.approve(req.recommendation_id, notes=req.notes)
    else:
        result = tgov.reject(req.recommendation_id, notes=req.notes)
    if not result:
        raise HTTPException(404, f"Recommendation {req.recommendation_id} not found")
    return result.model_dump()


@router.get("/recommendations")
def list_recommendations(status: str = None):
    tgov = TrainingGovernor()
    recs = tgov.list_recommendations(status=status)
    return {"recommendations": [r.model_dump() for r in recs]}
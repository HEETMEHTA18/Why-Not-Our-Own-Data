from fastapi import APIRouter, Query
from .models import KnowledgeCategory, ClassificationRequest
from .engine import KnowledgeClassifier

router = APIRouter(prefix="/classify", tags=["classifier"])
engine = KnowledgeClassifier()


@router.post("/text")
def classify_text(req: ClassificationRequest):
    results = engine.classify_text(req.text, title=req.title)
    return {
        "classifications": [
            {"category": c.value, "confidence": round(conf, 4), "signals": sigs}
            for c, conf, sigs in results
        ]
    }


@router.post("/item")
def classify_item(item_id: str = Query(...), text: str = Query(...), item_type: str = "crawled", title: str = None):
    verdict = engine.classify_item(item_id, text, item_type=item_type, title=title)
    return verdict.model_dump()


@router.post("/run-on-extracted")
def classify_extracted():
    count = engine.classify_extracted_knowledge()
    return {"classified": count}


@router.get("/verdicts")
def get_verdicts(category: str = None, limit: int = 50, offset: int = 0):
    verdicts = engine.get_verdicts(category=category, limit=limit, offset=offset)
    return {"total": len(verdicts), "verdicts": verdicts}


@router.get("/stats")
def get_stats():
    return engine.stats()


@router.get("/categories")
def get_categories():
    return {"categories": [c.value for c in KnowledgeCategory]}

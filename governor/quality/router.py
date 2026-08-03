from fastapi import APIRouter, Depends
from .scorer import QualityScorer
from .metrics import QualityMetrics
from ..config import settings

router = APIRouter(prefix="/quality", tags=["quality"])


def get_scorer() -> QualityScorer:
    return QualityScorer()


@router.post("/score-all")
def score_all(scorer: QualityScorer = Depends(get_scorer)):
    scores = scorer.score_all()
    return {"scored": len(scores)}


@router.get("/report")
def quality_report(scorer: QualityScorer = Depends(get_scorer)):
    scores = scorer.get_all_scores()
    if not scores:
        return {"message": "No scores yet", "total_scored": 0}
    report = QualityMetrics.report(scores)
    report["threshold"] = settings.quality_threshold
    report["distribution"] = QualityMetrics.distribution(scores)
    return report


@router.get("/scores/{example_id}")
def get_scores(example_id: str, scorer: QualityScorer = Depends(get_scorer)):
    return scorer.get_scores(example_id)

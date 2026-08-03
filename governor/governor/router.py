from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from .engine import TrainingGovernor
from .models import GovernorDecision, ApproveRequest, TrainingRecommendation

router = APIRouter(prefix="/governor", tags=["governor"])


def get_governor() -> TrainingGovernor:
    return TrainingGovernor()


@router.get("/recommend-training", response_model=GovernorDecision)
def recommend_training(governor: TrainingGovernor = Depends(get_governor)):
    return governor.evaluate()


@router.post("/approve", response_model=TrainingRecommendation)
def approve_training(req: ApproveRequest, governor: TrainingGovernor = Depends(get_governor)):
    if req.approved:
        rec = governor.approve(req.recommendation_id, req.notes)
    else:
        rec = governor.reject(req.recommendation_id, req.notes)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec


@router.get("/recommendations", response_model=list)
def list_recommendations(status: Optional[str] = None, governor: TrainingGovernor = Depends(get_governor)):
    return governor.list_recommendations(status)


@router.get("/recommendation/{rec_id}", response_model=TrainingRecommendation)
def get_recommendation(rec_id: str, governor: TrainingGovernor = Depends(get_governor)):
    rec = governor.get_recommendation(rec_id)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec

from fastapi import APIRouter, Depends, HTTPException
from .manager import ConsentManager
from .models import ConsentPrompt, ConsentResponse

router = APIRouter(prefix="/consent", tags=["consent"])


def get_manager() -> ConsentManager:
    return ConsentManager()


@router.get("/prompt/{recommendation_id}", response_model=ConsentPrompt)
def get_prompt(recommendation_id: str, manager: ConsentManager = Depends(get_manager)):
    prompt = manager.build_prompt(recommendation_id)
    if not prompt:
        raise HTTPException(404, "Recommendation not found")
    return prompt


@router.post("/respond")
def respond(response: ConsentResponse, manager: ConsentManager = Depends(get_manager)):
    success = manager.record_decision(response)
    return {"recorded": True, "approved": success, "decision": response.decision}

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .classifier import MemoryClassifier
from .kb import KnowledgeBase
from .models import ClassificationResult

router = APIRouter(prefix="/memory", tags=["memory"])


def get_classifier() -> MemoryClassifier:
    return MemoryClassifier()


def get_kb():
    from .kb import KnowledgeBase
    return KnowledgeBase()


@router.post("/classify/{conversation_id}", response_model=ClassificationResult)
def classify(conversation_id: str, classifier: MemoryClassifier = Depends(get_classifier)):
    try:
        return classifier.classify(conversation_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/classify-many", response_model=List[ClassificationResult])
def classify_many(conversation_ids: List[str], classifier: MemoryClassifier = Depends(get_classifier)):
    return classifier.classify_many(conversation_ids)


@router.get("/classification/{conversation_id}", response_model=ClassificationResult)
def get_classification(conversation_id: str, classifier: MemoryClassifier = Depends(get_classifier)):
    result = classifier.get_classification(conversation_id)
    if not result:
        raise HTTPException(404, "Not yet classified")
    return result


@router.get("/stats")
def memory_stats(classifier: MemoryClassifier = Depends(get_classifier), kb: KnowledgeBase = Depends(get_kb)):
    return {"classification_counts": classifier.stats(), "kb_size": kb.size()}


@router.post("/kb/store/{conversation_id}")
def store_in_kb(conversation_id: str, classifier: MemoryClassifier = Depends(get_classifier),
                kb: KnowledgeBase = Depends(get_kb)):
    result = classifier.get_classification(conversation_id)
    if not result:
        raise HTTPException(400, "Classify the conversation first")
    kb.store(conversation_id, result.reason, result.classification)
    return {"stored": True, "classification": result.classification.value}


@router.get("/kb/search")
def search_kb(query: str, kb: KnowledgeBase = Depends(get_kb)):
    return {"results": kb.search(query)}

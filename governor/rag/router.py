from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from .retrieval import RAGKnowledgeBase

router = APIRouter(prefix="/rag", tags=["rag"])

_kb: Optional[RAGKnowledgeBase] = None


def get_kb() -> RAGKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = RAGKnowledgeBase()
    return _kb


class RagDocumentRequest(BaseModel):
    knowledge_id: str
    title: str = ""
    content: str
    knowledge_type: str = "unknown"
    source: str = ""


class RagQueryRequest(BaseModel):
    query: str
    k: int = 5
    knowledge_type: str = ""
    compress: bool = False


@router.post("/add")
def add_document(req: RagDocumentRequest):
    kb = get_kb()
    doc_id = kb.add(req.knowledge_id, req.title, req.content, req.knowledge_type, req.source)
    return {"doc_id": doc_id, "stored": True}


@router.post("/retrieve")
def retrieve(req: RagQueryRequest):
    kb = get_kb()
    return kb.build_context(req.query, req.k, req.knowledge_type, compress=req.compress)


@router.get("/stats")
def stats():
    return get_kb().stats()

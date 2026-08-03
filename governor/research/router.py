from fastapi import APIRouter, Query
from .models import ResearchStatus, FeasibilityVerdict
from .engine import ResearchEngine

router = APIRouter(prefix="/research", tags=["research"])
engine = ResearchEngine()


@router.post("/seed-topics")
def seed_topics():
    count = engine.seed_topics()
    return {"seeded": count, "message": "Already seeded" if count == 0 else "Topics created"}


@router.get("/topics")
def list_topics(status: str = None):
    topics = engine.list_topics(status=status)
    return {"total": len(topics), "topics": topics}


@router.get("/topics/{topic_id}")
def get_topic(topic_id: str):
    topic = engine.get_topic(topic_id)
    return topic or {"error": "not found"}


@router.patch("/topics/{topic_id}")
def update_topic(topic_id: str, status: str = None, findings: str = None):
    kwargs = {}
    if status:
        kwargs["status"] = ResearchStatus(status)
    if findings:
        kwargs["findings"] = findings
    if not kwargs:
        return {"error": "no fields to update"}
    success = engine.update_topic(topic_id, **kwargs)
    return {"success": success}


@router.post("/papers")
def add_paper(title: str = Query(...), authors: str = Query(...), year: int = Query(...),
              url: str = "", abstract: str = "", key_findings: str = ""):
    author_list = [a.strip() for a in authors.split(",")]
    paper = engine.add_paper(title, author_list, year, url, abstract, key_findings)
    return paper.model_dump()


@router.get("/papers")
def list_papers(limit: int = 50):
    papers = engine.list_papers(limit=limit)
    return {"total": len(papers), "papers": papers}


@router.post("/feasibility")
def create_feasibility(topic_id: str = Query(...), verdict: str = Query(...), rationale: str = "",
                       risks: str = "", prerequisites: str = "", estimated_effort: str = "",
                       recommendations: str = ""):
    risk_list = [r.strip() for r in risks.split(",")] if risks else []
    prereq_list = [p.strip() for p in prerequisites.split(",")] if prerequisites else []
    rec_list = [r.strip() for r in recommendations.split(",")] if recommendations else []
    study = engine.feasibility_study(topic_id, FeasibilityVerdict(verdict), rationale,
                                      risk_list, prereq_list, estimated_effort, rec_list)
    return study.model_dump()


@router.get("/feasibility")
def list_feasibility(topic_id: str = None):
    studies = engine.list_feasibility(topic_id=topic_id)
    return {"total": len(studies), "studies": studies}


@router.get("/stats")
def get_stats():
    return engine.stats()

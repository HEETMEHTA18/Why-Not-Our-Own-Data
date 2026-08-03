from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .scheduler import PipelineScheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

_scheduler: Optional[PipelineScheduler] = None


def get_scheduler() -> PipelineScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
    return _scheduler


class RegisterJobRequest(BaseModel):
    name: str
    pipeline_name: str
    interval_minutes: int = 0
    cron_expression: str = ""
    config: dict = {}


@router.get("/jobs")
def list_jobs():
    sched = get_scheduler()
    return {"jobs": sched.get_jobs()}


@router.post("/jobs")
def register_job(req: RegisterJobRequest):
    sched = get_scheduler()
    job_id = sched.register_job(
        name=req.name,
        pipeline_name=req.pipeline_name,
        interval_minutes=req.interval_minutes,
        cron_expression=req.cron_expression or None,
        config=req.config,
    )
    return {"job_id": job_id, "name": req.name}


@router.post("/jobs/init-defaults")
def init_default_jobs():
    sched = get_scheduler()
    sched.register_default_jobs()
    return {"initialized": True, "count": 3}


@router.post("/jobs/{job_id}/toggle")
def toggle_job(job_id: str, enabled: bool):
    sched = get_scheduler()
    sched.enable_job(job_id, enabled)
    return {"job_id": job_id, "enabled": enabled}


@router.get("/logs")
def get_logs(limit: int = 50):
    sched = get_scheduler()
    return {"logs": sched.get_logs(limit)}
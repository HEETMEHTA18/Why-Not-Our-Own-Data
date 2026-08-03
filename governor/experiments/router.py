from fastapi import APIRouter, Query
from .models import ExperimentStatus
from .engine import ExperimentEngine

router = APIRouter(prefix="/experiments", tags=["experiments"])
engine = ExperimentEngine()


@router.post("/seed")
def seed_experiments():
    count = engine.seed_experiments()
    return {"seeded": count, "message": "Already seeded" if count == 0 else "Experiments created"}


@router.get("/configs")
def list_experiments():
    experiments = engine.list_experiments()
    return {"total": len(experiments), "experiments": experiments}


@router.get("/configs/{experiment_id}")
def get_experiment(experiment_id: str):
    exp = engine.get_experiment(experiment_id)
    return exp or {"error": "not found"}


@router.post("/configs/{experiment_id}/run")
def create_run(experiment_id: str):
    run = engine.create_run(experiment_id)
    return run.model_dump()


@router.get("/runs/{experiment_id}")
def list_runs(experiment_id: str):
    runs = engine.list_runs(experiment_id)
    return {"total": len(runs), "runs": runs}


@router.patch("/runs/{run_id}")
def update_run(run_id: str, status: str = None, results: str = None, metrics: str = None,
               duration_seconds: float = None, error: str = None):
    kwargs = {}
    if status:
        kwargs["status"] = ExperimentStatus(status)
    if results:
        kwargs["results"] = results
    if metrics:
        kwargs["metrics"] = metrics
    if duration_seconds is not None:
        kwargs["duration_seconds"] = duration_seconds
    if error:
        kwargs["error"] = error
    success = engine.update_run(run_id, **kwargs)
    return {"success": success}


@router.post("/reports")
def create_report(experiment_id: str = Query(...), summary: str = Query(...),
                  findings: str = "", conclusion: str = "", recommendations: str = ""):
    rec_list = [r.strip() for r in recommendations.split(",")] if recommendations else []
    report = engine.create_report(experiment_id, summary, findings, conclusion, rec_list)
    return report.model_dump()


@router.get("/reports")
def list_reports(experiment_id: str = None):
    reports = engine.list_reports(experiment_id=experiment_id)
    return {"total": len(reports), "reports": reports}


@router.get("/stats")
def get_stats():
    return engine.stats()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from .consensus import GovernanceCouncil, COUNCIL_MEMBERS
from .feedback import FeedbackEngine
from .insights import AdapterRouter, LineageTracker
from .ops import CostTelemetry, AlertEngine, LearningProfiler

router = APIRouter(prefix="/platform", tags=["platform"])

_council: Optional[GovernanceCouncil] = None
_feedback: Optional[FeedbackEngine] = None
_router_engine: Optional[AdapterRouter] = None
_lineage: Optional[LineageTracker] = None
_telemetry: Optional[CostTelemetry] = None
_alerts: Optional[AlertEngine] = None
_profiler: Optional[LearningProfiler] = None


def get_council() -> GovernanceCouncil:
    global _council
    if _council is None:
        _council = GovernanceCouncil()
    return _council


def get_feedback() -> FeedbackEngine:
    global _feedback
    if _feedback is None:
        _feedback = FeedbackEngine()
    return _feedback


def get_router_engine() -> AdapterRouter:
    global _router_engine
    if _router_engine is None:
        _router_engine = AdapterRouter()
    return _router_engine


def get_lineage() -> LineageTracker:
    global _lineage
    if _lineage is None:
        _lineage = LineageTracker()
    return _lineage


def get_telemetry() -> CostTelemetry:
    global _telemetry
    if _telemetry is None:
        _telemetry = CostTelemetry()
    return _telemetry


def get_alerts() -> AlertEngine:
    global _alerts
    if _alerts is None:
        _alerts = AlertEngine()
    return _alerts


def get_profiler() -> LearningProfiler:
    global _profiler
    if _profiler is None:
        _profiler = LearningProfiler()
    return _profiler


# --- Consensus ------------------------------------------------------------

class ConsensusRequest(BaseModel):
    knowledge_id: str
    text: str
    title: str = ""
    knowledge_type: str = ""
    confidence: float = 0.0
    metadata: dict = {}


@router.post("/consensus/decide")
def consensus_decide(req: ConsensusRequest):
    council = get_council()
    decision = council.decide(req.knowledge_id, req.text, req.title,
                              req.knowledge_type, req.confidence, req.metadata)
    return decision.to_dict()


@router.get("/consensus/members")
def consensus_members():
    return {"members": COUNCIL_MEMBERS}


@router.get("/consensus/stats")
def consensus_stats():
    return get_council().get_stats()


@router.get("/consensus/recent")
def consensus_recent(limit: int = 50):
    return {"decisions": get_council().recent(limit)}


# --- Feedback / self-tuning governor --------------------------------------

class RegressionRequest(BaseModel):
    task: str
    delta_score: float
    knowledge_type: str = ""


@router.post("/feedback/regression")
def record_regression(req: RegressionRequest):
    engine = get_feedback()
    return engine.record_regression(req.task, req.delta_score, req.knowledge_type)


@router.get("/feedback/thresholds")
def current_thresholds():
    return {"thresholds": get_feedback().get_current_thresholds()}


@router.get("/feedback/history")
def tuning_history(limit: int = 50):
    return {"tuning": get_feedback().get_tuning_history(limit)}


@router.post("/feedback/reset")
def reset_thresholds():
    count = get_feedback().reset_to_defaults()
    return {"reset": count}


# --- Adapter routing + lineage ---------------------------------------------

class RegisterAdapterRequest(BaseModel):
    adapter_id: str
    domain: str
    benchmark_score: float = 0.0
    baseline_score: float = 0.0


class RouteRequest(BaseModel):
    prompt: str


@router.post("/routing/register")
def register_adapter(req: RegisterAdapterRequest):
    router_engine = get_router_engine()
    router_engine.register_adapter(req.adapter_id, req.domain,
                                   req.benchmark_score, req.baseline_score)
    return {"registered": True}


@router.post("/routing/route")
def route_prompt(req: RouteRequest):
    router_engine = get_router_engine()
    return router_engine.route(req.prompt)


@router.get("/routing/stats")
def routing_stats():
    return get_router_engine().routing_stats()


@router.get("/routing/adapters")
def routing_adapters():
    return {"adapters": get_router_engine().registered_adapters()}


class LinkRequest(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    link_type: str = "derived_from"
    metadata: dict = {}


@router.post("/lineage/link")
def lineage_link(req: LinkRequest):
    tracker = get_lineage()
    lid = tracker.link(req.source_type, req.source_id, req.target_type,
                       req.target_id, req.link_type, req.metadata)
    return {"link_id": lid}


@router.get("/lineage/trace")
def lineage_trace(target_type: str, target_id: str, max_depth: int = 3):
    tracker = get_lineage()
    return tracker.trace(target_type, target_id, max_depth)


# --- Cost telemetry ---------------------------------------------------------

class RunRequest(BaseModel):
    adapter_id: str = "base"
    task: str = ""
    gpu_hours: float = 0.0
    gpu_type: str = "unknown"
    benchmark_delta: float = 0.0


@router.post("/telemetry/record")
def record_run(req: RunRequest):
    rid = get_telemetry().record(req.adapter_id, req.task, req.gpu_hours,
                                 req.gpu_type, req.benchmark_delta)
    return {"run_id": rid}


@router.get("/telemetry/stats")
def telemetry_stats():
    return get_telemetry().stats()


@router.get("/telemetry/history")
def telemetry_history(limit: int = 50):
    return {"runs": get_telemetry().history(limit)}


# --- Alerts -----------------------------------------------------------------

class AlertRequest(BaseModel):
    severity: str = "medium"
    title: str
    message: str = ""
    event_type: str = ""
    payload: dict = {}
    webhook_url: str = ""


@router.post("/alerts/notify")
def create_alert(req: AlertRequest):
    aid = get_alerts().notify(req.severity, req.title, req.message,
                              req.event_type, req.payload, req.webhook_url)
    return {"alert_id": aid}


@router.get("/alerts")
def list_alerts(limit: int = 50):
    return {"alerts": get_alerts().list_alerts(limit)}


# --- Personalized profiler --------------------------------------------------

class ObserveRequest(BaseModel):
    text: str
    weight: float = 1.0


@router.post("/profiler/observe")
def observe(req: ObserveRequest):
    get_profiler().observe(req.text, req.weight)
    return {"observed": True}


@router.get("/profiler/profile")
def profile():
    return get_profiler().profile()

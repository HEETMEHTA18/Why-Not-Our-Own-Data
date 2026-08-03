from pydantic import BaseModel
from typing import Any, Optional, List
from enum import Enum
from datetime import datetime, timezone


class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    KNOWLEDGE_EXTRACTED = "knowledge.extracted"
    KNOWLEDGE_CLASSIFIED = "knowledge.classified"
    KNOWLEDGE_GOVERNED = "knowledge.governed"
    DATASET_BUILT = "dataset.built"
    DATASET_SCORED = "dataset.scored"
    TRAINING_RECOMMENDED = "training.recommended"
    TRAINING_STARTED = "training.started"
    TRAINING_COMPLETED = "training.completed"
    TRAINING_FAILED = "training.failed"
    BENCHMARK_STARTED = "benchmark.started"
    BENCHMARK_COMPLETED = "benchmark.completed"
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    ROLLBACK_EXECUTED = "rollback.executed"
    RESEARCH_FINDING = "research.finding"
    DOCUMENTATION_UPDATE = "documentation.update"
    GOVERNOR_DECISION = "governor.decision"
    CRAWL_COMPLETED = "crawl.completed"
    ERROR_OCCURRED = "error.occurred"
    USER_APPROVAL_REQUIRED = "user.approval_required"
    USER_APPROVAL_RESULT = "user.approval_result"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    CONSENSUS_REACHED = "consensus.reached"
    CONSENSUS_DISPUTED = "consensus.disputed"
    GOVERNOR_TUNED = "governor.tuned"
    BENCHMARK_REGRESSED = "benchmark.regressed"
    ROUTE_DECIDED = "route.decided"
    ALERT_TRIGGERED = "alert.triggered"
    KNOWLEDGE_INGESTED_KG = "knowledge.ingested_kg"


class Event(BaseModel):
    id: str
    type: EventType
    source: str
    payload: dict = {}
    priority: EventPriority = EventPriority.MEDIUM
    correlation_id: Optional[str] = None
    timestamp: str = ""
    metadata: dict = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())


class Subscription(BaseModel):
    event_type: EventType
    callback_name: str
    filter_fn: Optional[str] = None


class EventBusStats(BaseModel):
    total_events: int = 0
    events_by_type: dict = {}
    active_subscriptions: int = 0
    queue_depth: int = 0
    failed_events: int = 0
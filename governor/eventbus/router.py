from fastapi import APIRouter
from .bus import get_bus
from .models import Event, EventType, EventPriority

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stats")
def get_stats():
    bus = get_bus()
    return bus.get_stats().model_dump()


@router.get("/recent")
def get_recent(limit: int = 50):
    bus = get_bus()
    return [e.model_dump() for e in bus.get_recent_events(limit)]


@router.post("/publish")
async def publish_event(event_type: str, source: str, payload: dict = None,
                        priority: str = "medium", correlation_id: str = None):
    bus = get_bus()
    try:
        et = EventType(event_type)
    except ValueError:
        return {"error": f"unknown event type: {event_type}"}
    try:
        ep = EventPriority(priority)
    except ValueError:
        ep = EventPriority.MEDIUM
    event = await bus.publish_sync(et, source, payload, ep, correlation_id)
    return {"published": True, "event_id": event.id, "type": event.type.value}
import asyncio
import uuid
import json
import structlog
from datetime import datetime, timezone
from typing import Callable, Coroutine, Any, Optional, Dict, List, Set
from collections import defaultdict

from .models import Event, EventType, EventPriority, EventBusStats

logger = structlog.get_logger()


class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Dict[str, Any]]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = 1000
        self._failed_count = 0
        self._total_count = 0
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: EventType, callback: Callable[[Event], Coroutine[Any, Any, None]],
                  name: str = "", filter_fn: Optional[Callable[[Event], bool]] = None) -> str:
        sub_id = str(uuid.uuid4())
        self._subscribers[event_type].append({
            "id": sub_id,
            "callback": callback,
            "name": name or callback.__name__,
            "filter_fn": filter_fn,
        })
        logger.debug("subscription_added", event_type=event_type.value, subscriber=name)
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        for event_type in list(self._subscribers.keys()):
            self._subscribers[event_type] = [
                s for s in self._subscribers[event_type] if s["id"] != sub_id
            ]
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
        return True

    async def publish(self, event: Event) -> None:
        self._total_count += 1
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        await self._queue.put(event)
        logger.debug("event_published", type=event.type.value, source=event.source)

    async def publish_sync(self, event_type: EventType, source: str, payload: dict = None,
                           priority: EventPriority = EventPriority.MEDIUM,
                           correlation_id: str = None) -> Event:
        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            source=source,
            payload=payload or {},
            priority=priority,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await self.publish(event)
        return event

    async def _process_event(self, event: Event) -> None:
        subscribers = self._subscribers.get(event.type, []) + self._subscribers.get(EventType("*"), [])
        if not subscribers:
            return

        results = []
        for sub in subscribers:
            try:
                if sub["filter_fn"] and not sub["filter_fn"](event):
                    continue
                if asyncio.iscoroutinefunction(sub["callback"]):
                    await sub["callback"](event)
                else:
                    sub["callback"](event)
                results.append(sub["name"])
            except Exception as e:
                self._failed_count += 1
                logger.error("event_handler_failed", event_type=event.type.value,
                             handler=sub["name"], error=str(e))

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_event(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._failed_count += 1
                logger.error("event_worker_error", error=str(e))

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("event_bus_started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("event_bus_stopped", processed=self._total_count, failed=self._failed_count)

    def get_stats(self) -> EventBusStats:
        by_type = defaultdict(int)
        for event in self._history:
            by_type[event.type.value] += 1
        return EventBusStats(
            total_events=self._total_count,
            events_by_type=dict(by_type),
            active_subscriptions=sum(len(v) for v in self._subscribers.values()),
            queue_depth=self._queue.qsize(),
            failed_events=self._failed_count,
        )

    def get_recent_events(self, limit: int = 50) -> List[Event]:
        return self._history[-limit:]


_shared_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    global _shared_bus
    if _shared_bus is None:
        _shared_bus = EventBus()
    return _shared_bus
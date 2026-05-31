"""Event bus — ring buffer + execution_log.jsonl + SSE subscribers (Phase 2)."""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.api.run_event import EVENT_LABELS, RunEvent, RunEventType
from src.agent.runtime_state import RunState
from src.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventBus:
    """
    Layer A — Real-time Timeline stream.

    - In-memory ring buffer (recent N events) for hot replay
    - execution_log.jsonl for durable timeline persistence
    - SSE subscribers via asyncio queues

    Audit log (wal.jsonl / audit_log.jsonl) is separate — Layer B, debug/recovery only.
    """

    def __init__(self, run_id: str, run_dir: Path) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.log_path = run_dir / "execution_log.jsonl"
        self._buffer: deque[RunEvent] = deque(maxlen=settings.event_buffer_size)
        self._subscribers: list[asyncio.Queue[RunEvent | None]] = []
        self._lock = asyncio.Lock()
        self._closed = False
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._hydrate_buffer_from_disk()

    def _hydrate_buffer_from_disk(self) -> None:
        for event in self._read_disk_all():
            self._buffer.append(event)

    def _append_disk(self, event: RunEvent) -> None:
        line = event.model_dump_json(by_alias=True) + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    async def publish(
        self,
        event_type: RunEventType,
        *,
        run_state: RunState,
        message: str,
        description: str = "",
        iteration: int = 0,
        tool: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RunEvent:
        event = RunEvent(
            eventId=str(uuid.uuid4()),
            runId=self.run_id,
            timestamp=_utcnow(),
            type=event_type,
            runState=run_state,
            label=EVENT_LABELS.get(event_type, event_type.value),
            message=message,
            description=description,
            iteration=iteration,
            tool=tool,
            payload=payload or {},
        )
        async with self._lock:
            self._buffer.append(event)
            self._append_disk(event)
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        return event

    def recent(self, limit: int | None = None) -> list[RunEvent]:
        items = list(self._buffer)
        if limit is not None:
            return items[-limit:]
        return items

    def after_event_id(self, after_id: str | None, *, limit: int | None = None) -> list[RunEvent]:
        """Replay events after after_id — buffer first, fallback to execution_log.jsonl."""
        if not after_id:
            return self.recent(limit)

        buffer_ids = {e.event_id for e in self._buffer}
        if after_id in buffer_ids or self._buffer:
            all_in_buffer = list(self._buffer)
            found = False
            result: list[RunEvent] = []
            for ev in all_in_buffer:
                if found:
                    result.append(ev)
                elif ev.event_id == after_id:
                    found = True
            if found:
                return result[-settings.event_buffer_size :] if limit is None else result[-limit:]

        disk_events = self._read_disk_all()
        found = False
        result = []
        for ev in disk_events:
            if found:
                result.append(ev)
            elif ev.event_id == after_id:
                found = True
        if limit is not None:
            return result[-limit:]
        return result

    def _read_disk_all(self) -> list[RunEvent]:
        if not self.log_path.exists():
            return []
        events: list[RunEvent] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(RunEvent.model_validate_json(line))
        return events

    def load_all_from_disk(self) -> list[RunEvent]:
        return self._read_disk_all()

    def subscribe(self) -> asyncio.Queue[RunEvent | None]:
        queue: asyncio.Queue[RunEvent | None] = asyncio.Queue(maxsize=512)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RunEvent | None]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def close_subscribers(self) -> None:
        self._closed = True
        for queue in self._subscribers:
            await queue.put(None)


_buses: dict[str, EventBus] = {}


def get_or_create_bus(run_id: str, run_dir: Path) -> EventBus:
    if run_id not in _buses:
        _buses[run_id] = EventBus(run_id, run_dir)
    return _buses[run_id]


def get_bus(run_id: str) -> EventBus | None:
    return _buses.get(run_id)


def clear_buses() -> None:
    _buses.clear()

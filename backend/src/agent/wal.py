"""Write-Ahead Log — Phase 1 foundation for transactional runtime."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.agent.runtime_state import RunState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WalEventType(str, Enum):
    RUN_CREATED = "run_created"
    STATE_CHANGED = "state_changed"
    PLAN_PROPOSED = "plan_proposed"
    TOOL_INTENT = "tool_intent"
    TOOL_STARTED = "tool_started"
    TOOL_COMMITTED = "tool_committed"
    TOOL_FAILED = "tool_failed"
    FILE_WRITE_INTENT = "file_write_intent"
    FILE_WRITE_STAGED = "file_write_staged"
    FILE_WRITE_COMMITTED = "file_write_committed"
    FILE_WRITE_FAILED = "file_write_failed"
    ARTIFACT_REGISTERED = "artifact_registered"
    RESEARCH_FINDINGS_EXTRACTED = "research_findings_extracted"
    RESEARCH_SYNTHESIS_STARTED = "research_synthesis_started"
    RESEARCH_SYNTHESIS_COMMITTED = "research_synthesis_committed"
    SNAPSHOT_CREATED = "snapshot_created"
    QUALITY_CHECK_STARTED = "quality_check_started"
    QUALITY_CHECK_PASSED = "quality_check_passed"
    QUALITY_CHECK_FAILED = "quality_check_failed"
    FINALIZE_INTENT = "finalize_intent"
    FINALIZE_COMMITTED = "finalize_committed"
    WAL_REPLAY_STARTED = "wal_replay_started"
    WAL_REPLAY_COMPLETED = "wal_replay_completed"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    RETRY_REQUESTED = "retry_requested"
    RESUME_REQUESTED = "resume_requested"
    MEMORY_COMPACTION_STARTED = "memory_compaction_started"
    MEMORY_COMPACTION_COMPLETED = "memory_compaction_completed"
    QUALITY_REVISION_STARTED = "quality_revision_started"
    QUALITY_CIRCUIT_BREAKER_TRIGGERED = "quality_circuit_breaker_triggered"


class WalEvent(BaseModel):
    event_id: str = Field(alias="eventId")
    run_id: str = Field(alias="runId")
    type: WalEventType
    timestamp: datetime
    state_before: RunState | None = Field(default=None, alias="stateBefore")
    state_after: RunState | None = Field(default=None, alias="stateAfter")
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class WalWriter:
    """Append-only JSONL write-ahead log."""

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.wal_path = run_dir / "wal.jsonl"
        self.audit_path = run_dir / "audit_log.jsonl"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: WalEventType,
        *,
        state_before: RunState | None = None,
        state_after: RunState | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WalEvent:
        event = WalEvent(
            eventId=str(uuid.uuid4()),
            runId=self.run_id,
            type=event_type,
            timestamp=_utcnow(),
            stateBefore=state_before,
            stateAfter=state_after,
            payload=payload or {},
        )
        line = event.model_dump_json(by_alias=True) + "\n"
        with open(self.wal_path, "a", encoding="utf-8") as f:
            f.write(line)
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(line)
        return event

    def read_all(self) -> list[WalEvent]:
        if not self.wal_path.exists():
            return []
        events: list[WalEvent] = []
        for line in self.wal_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(WalEvent.model_validate_json(line))
        return events

    def read_audit_all(self) -> list[WalEvent]:
        if not self.audit_path.exists():
            return []
        events: list[WalEvent] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(WalEvent.model_validate_json(line))
        return events

"""In-memory status snapshot cache — GET /status reads ONLY this layer (Phase 1)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agent.runtime_state import (
    LEGACY_STATUS_MAP,
    RUN_STATE_LABELS,
    RunState,
    TERMINAL_STATES,
)
from src.config import settings

# Hot-path cache: runId -> snapshot. Status API must not read WAL / workspace / artifacts content.
active_snapshots: dict[str, "RunStatusSnapshot"] = {}
_pending_disk_writes: dict[str, asyncio.Task] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactMeta(BaseModel):
    name: str
    type: str
    path: str
    url: str
    size: int
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class RunStatusSnapshot(BaseModel):
    run_id: str = Field(alias="runId")
    goal: str
    run_state: RunState = Field(alias="runState")
    run_state_label: str = Field(alias="runStateLabel")
    legacy_status: str = Field(alias="legacyStatus")
    current_step: str | None = Field(default=None, alias="currentStep")
    current_tool: str | None = Field(default=None, alias="currentTool")
    thinking_message: str | None = Field(default=None, alias="thinkingMessage")
    latest_reasoning: str | None = Field(default=None, alias="latestReasoning")
    latest_tool_result: dict[str, Any] | None = Field(default=None, alias="latestToolResult")
    progress: float = 0.0
    artifacts: list[ArtifactMeta] = Field(default_factory=list)
    error: str | None = None
    stop_reason: str | None = Field(default=None, alias="stopReason")
    revision_attempt: int = Field(default=0, alias="revisionAttempt")
    iteration: int = 0
    demo_mode: bool = Field(default=False, alias="demoMode")
    task_type: str = Field(default="research_report", alias="taskType")
    started_at: datetime = Field(alias="startedAt")
    updated_at: datetime = Field(alias="updatedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    heartbeat_at: datetime = Field(alias="heartbeatAt")
    is_stale: bool = Field(default=False, alias="isStale")
    sync_delayed: bool = Field(default=False, alias="syncDelayed")

    model_config = {"populate_by_name": True}


class SnapshotManager:
    """Memory-first snapshot with debounced async disk flush."""

    def upsert(self, snapshot: RunStatusSnapshot, run_dir: Path | None = None) -> None:
        snapshot.updated_at = _utcnow()
        active_snapshots[snapshot.run_id] = snapshot
        if run_dir is not None:
            self._schedule_disk_flush(snapshot, run_dir)

    def get(self, run_id: str) -> RunStatusSnapshot | None:
        return active_snapshots.get(run_id)

    def remove(self, run_id: str) -> None:
        active_snapshots.pop(run_id, None)
        task = _pending_disk_writes.pop(run_id, None)
        if task and not task.done():
            task.cancel()

    def load_cold(self, run_id: str, run_dir: Path) -> RunStatusSnapshot | None:
        if run_id in active_snapshots:
            return active_snapshots[run_id]
        path = run_dir / "snapshot.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshot = RunStatusSnapshot.model_validate(data)
        active_snapshots[run_id] = snapshot
        return snapshot

    def _schedule_disk_flush(self, snapshot: RunStatusSnapshot, run_dir: Path) -> None:
        run_id = snapshot.run_id
        existing = _pending_disk_writes.get(run_id)
        if existing and not existing.done():
            existing.cancel()

        async def _write() -> None:
            await asyncio.sleep(settings.snapshot_flush_delay_seconds)
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshot.json").write_text(
                snapshot.model_dump_json(by_alias=True, indent=2),
                encoding="utf-8",
            )

        try:
            loop = asyncio.get_running_loop()
            _pending_disk_writes[run_id] = loop.create_task(_write())
        except RuntimeError:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshot.json").write_text(
                snapshot.model_dump_json(by_alias=True, indent=2),
                encoding="utf-8",
            )


snapshot_manager = SnapshotManager()


def build_snapshot(
    *,
    run_id: str,
    goal: str,
    run_state: RunState,
    progress: float = 0.0,
    current_step: str | None = None,
    current_tool: str | None = None,
    thinking_message: str | None = None,
    latest_reasoning: str | None = None,
    latest_tool_result: dict[str, Any] | None = None,
    artifacts: list[ArtifactMeta] | None = None,
    error: str | None = None,
    stop_reason: str | None = None,
    revision_attempt: int = 0,
    iteration: int = 0,
    demo_mode: bool = False,
    task_type: str = "research_report",
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    heartbeat_at: datetime | None = None,
    sync_delayed: bool = False,
) -> RunStatusSnapshot:
    now = _utcnow()
    hb = heartbeat_at or now
    threshold = timedelta(seconds=settings.stale_threshold_seconds)
    hb_utc = hb if hb.tzinfo else hb.replace(tzinfo=timezone.utc)
    is_stale = run_state not in TERMINAL_STATES and (now - hb_utc) > threshold
    return RunStatusSnapshot(
        runId=run_id,
        goal=goal,
        runState=run_state,
        runStateLabel=RUN_STATE_LABELS.get(run_state, run_state.value),
        legacyStatus=LEGACY_STATUS_MAP.get(run_state, "running"),
        currentStep=current_step,
        currentTool=current_tool,
        thinkingMessage=thinking_message,
        latestReasoning=latest_reasoning,
        latestToolResult=latest_tool_result,
        progress=progress,
        artifacts=artifacts or [],
        error=error,
        stopReason=stop_reason,
        revisionAttempt=revision_attempt,
        iteration=iteration,
        demoMode=demo_mode,
        taskType=task_type,
        startedAt=started_at or now,
        updatedAt=now,
        finishedAt=finished_at,
        heartbeatAt=hb,
        isStale=is_stale,
        syncDelayed=sync_delayed,
    )

"""Checkpoint persistence — planner context + run metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.agent.runtime_state import PlannerContext, RunState, TaskType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CheckpointData(BaseModel):
    run_id: str
    goal: str
    task_type: TaskType = TaskType.RESEARCH_REPORT
    demo_mode: bool = False
    scenario: str | None = None
    run_state: RunState
    iteration: int = 0
    revision_attempt: int = 0
    retry_count: int = 0
    stop_reason: str | None = None
    error: str | None = None
    progress: float = 0.0
    current_step: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    planner_context: PlannerContext | None = None
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


class CheckpointStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.path = run_dir / "checkpoint.json"

    def save(self, data: CheckpointData) -> None:
        data.updated_at = _utcnow()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data.model_dump_json(indent=2), encoding="utf-8")

    def load(self) -> CheckpointData | None:
        if not self.path.exists():
            return None
        return CheckpointData.model_validate_json(self.path.read_text(encoding="utf-8"))

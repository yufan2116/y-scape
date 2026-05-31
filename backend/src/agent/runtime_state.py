"""Run state definitions — shared semantics for backend and frontend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    THINKING = "thinking"
    TOOL_PENDING = "tool_pending"
    TOOL_RUNNING = "tool_running"
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILED = "tool_failed"
    SYNTHESIZING_RESEARCH = "synthesizing_research"
    WRITING_ARTIFACT = "writing_artifact"
    FINALIZING = "finalizing"
    SUCCESS = "success"
    DEGRADED_SUCCESS = "degraded_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    NEEDS_INPUT = "needs_input"
    STALE = "stale"
    RECOVERING = "recovering"
    RETRYING = "retrying"
    INTERRUPTED = "interrupted"
    # Transactional runtime (Section XVIII)
    WAL_REPLAYING = "wal_replaying"
    CHECKPOINT_RESTORING = "checkpoint_restoring"
    MEMORY_COMPACTING = "memory_compacting"
    QUALITY_REVISION = "quality_revision"
    QUALITY_BLOCKED = "quality_blocked"


TERMINAL_STATES: frozenset[RunState] = frozenset(
    {
        RunState.SUCCESS,
        RunState.DEGRADED_SUCCESS,
        RunState.FAILED,
        RunState.CANCELLED,
        RunState.TIMEOUT,
        RunState.NEEDS_INPUT,
        RunState.STALE,
        RunState.INTERRUPTED,
        RunState.QUALITY_BLOCKED,
    }
)


RUNNING_STATES: frozenset[RunState] = frozenset(
    s for s in RunState if s not in TERMINAL_STATES
)


RUN_STATE_LABELS: dict[RunState, str] = {
    RunState.CREATED: "已创建",
    RunState.PLANNING: "规划中",
    RunState.THINKING: "思考中",
    RunState.TOOL_PENDING: "工具待执行",
    RunState.TOOL_RUNNING: "工具运行中",
    RunState.TOOL_SUCCESS: "工具成功",
    RunState.TOOL_FAILED: "工具失败",
    RunState.SYNTHESIZING_RESEARCH: "研究综合中",
    RunState.WRITING_ARTIFACT: "写入交付物",
    RunState.FINALIZING: "收尾中",
    RunState.SUCCESS: "成功",
    RunState.DEGRADED_SUCCESS: "降级成功",
    RunState.FAILED: "失败",
    RunState.CANCELLED: "已取消",
    RunState.TIMEOUT: "超时",
    RunState.NEEDS_INPUT: "需要输入",
    RunState.STALE: "停滞",
    RunState.RECOVERING: "恢复中",
    RunState.RETRYING: "重试中",
    RunState.INTERRUPTED: "已中断",
    RunState.WAL_REPLAYING: "WAL 重放中",
    RunState.CHECKPOINT_RESTORING: "Checkpoint 恢复中",
    RunState.MEMORY_COMPACTING: "记忆压缩中",
    RunState.QUALITY_REVISION: "质量修订中",
    RunState.QUALITY_BLOCKED: "质量熔断",
}


LEGACY_STATUS_MAP: dict[RunState, str] = {
    RunState.CREATED: "pending",
    RunState.PLANNING: "running",
    RunState.THINKING: "running",
    RunState.TOOL_PENDING: "running",
    RunState.TOOL_RUNNING: "running",
    RunState.TOOL_SUCCESS: "running",
    RunState.TOOL_FAILED: "running",
    RunState.SYNTHESIZING_RESEARCH: "running",
    RunState.WRITING_ARTIFACT: "running",
    RunState.FINALIZING: "running",
    RunState.RECOVERING: "running",
    RunState.RETRYING: "running",
    RunState.WAL_REPLAYING: "running",
    RunState.CHECKPOINT_RESTORING: "running",
    RunState.MEMORY_COMPACTING: "running",
    RunState.QUALITY_REVISION: "running",
    RunState.SUCCESS: "completed",
    RunState.DEGRADED_SUCCESS: "completed",
    RunState.FAILED: "failed",
    RunState.CANCELLED: "cancelled",
    RunState.TIMEOUT: "timeout",
    RunState.NEEDS_INPUT: "needs_input",
    RunState.STALE: "stale",
    RunState.INTERRUPTED: "interrupted",
    RunState.QUALITY_BLOCKED: "failed",
}


class TaskType(str, Enum):
    RESEARCH_REPORT = "research_report"
    TECHNICAL_REPORT = "technical_report"
    SIMPLE_NOTE = "simple_note"
    CODE_OUTPUT = "code_output"


class LoopOutcome(str, Enum):
    CONTINUE = "continue"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class PlannerContext(BaseModel):
    """Persisted planner context for checkpoint / resume (Phase 7)."""

    goal: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    committed_tool_results: list[dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0
    revision_attempt: int = 0
    quality_failure_reasons: list[str] = Field(default_factory=list)
    last_plan: dict[str, Any] | None = None


class RunRecord(BaseModel):
    """In-memory run record owned by RunManager."""

    run_id: str
    goal: str
    task_type: TaskType = TaskType.RESEARCH_REPORT
    demo_mode: bool = False
    scenario: str | None = None
    run_state: RunState = RunState.CREATED
    iteration: int = 0
    revision_attempt: int = 0
    retry_count: int = 0
    stop_reason: str | None = None
    error: str | None = None
    current_step: str | None = "created"
    current_tool: str | None = None
    thinking_message: str | None = None
    latest_reasoning: str | None = None
    latest_tool_result: dict[str, Any] | None = None
    progress: float = 0.0
    artifacts_meta: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    heartbeat_at: datetime
    planner_context: PlannerContext | None = None

    model_config = {"use_enum_values": False}


def progress_for_state(state: RunState) -> float:
    mapping: dict[RunState, float] = {
        RunState.CREATED: 0.0,
        RunState.PLANNING: 0.05,
        RunState.THINKING: 0.1,
        RunState.TOOL_PENDING: 0.15,
        RunState.TOOL_RUNNING: 0.2,
        RunState.TOOL_SUCCESS: 0.3,
        RunState.TOOL_FAILED: 0.25,
        RunState.SYNTHESIZING_RESEARCH: 0.45,
        RunState.MEMORY_COMPACTING: 0.5,
        RunState.WRITING_ARTIFACT: 0.6,
        RunState.QUALITY_REVISION: 0.7,
        RunState.FINALIZING: 0.85,
        RunState.WAL_REPLAYING: 0.1,
        RunState.CHECKPOINT_RESTORING: 0.1,
        RunState.RECOVERING: 0.15,
        RunState.RETRYING: 0.15,
        RunState.SUCCESS: 1.0,
        RunState.DEGRADED_SUCCESS: 1.0,
        RunState.FAILED: 1.0,
        RunState.CANCELLED: 1.0,
        RunState.TIMEOUT: 1.0,
        RunState.QUALITY_BLOCKED: 1.0,
    }
    return mapping.get(state, 0.2)


def is_terminal(state: RunState) -> bool:
    return state in TERMINAL_STATES

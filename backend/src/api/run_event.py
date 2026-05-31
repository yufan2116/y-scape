"""Run event model — Timeline / SSE payload (Layer A: real-time stream)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.agent.runtime_state import RunState


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    PLANNER_STARTED = "planner_started"
    PLANNER_RESPONSE = "planner_response"
    TOOL_STARTED = "tool_started"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    ARTIFACT_WRITTEN = "artifact_written"
    QUALITY_CHECK_STARTED = "quality_check_started"
    QUALITY_CHECK_FAILED = "quality_check_failed"
    QUALITY_CHECK_PASSED = "quality_check_passed"
    RESEARCH_SYNTHESIZED = "research_synthesized"
    FINALIZING = "finalizing"
    RUN_SUCCEEDED = "run_succeeded"
    RUN_DEGRADED_SUCCESS = "run_degraded_success"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    RUN_TIMEOUT = "run_timeout"
    STATE_CHANGED = "state_changed"
    CHECKPOINT_SAVED = "checkpoint_saved"
    # Transactional runtime timeline events (Section XVIII)
    WAL_REPLAY_STARTED = "wal_replay_started"
    WAL_REPLAY_COMPLETED = "wal_replay_completed"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    MEMORY_COMPACTION_STARTED = "memory_compaction_started"
    MEMORY_COMPACTION_COMPLETED = "memory_compaction_completed"
    QUALITY_REVISION_STARTED = "quality_revision_started"
    QUALITY_CIRCUIT_BREAKER_TRIGGERED = "quality_circuit_breaker_triggered"


EVENT_LABELS: dict[RunEventType, str] = {
    RunEventType.RUN_STARTED: "任务已启动",
    RunEventType.PLANNER_STARTED: "规划器启动",
    RunEventType.PLANNER_RESPONSE: "规划器响应",
    RunEventType.TOOL_STARTED: "工具开始",
    RunEventType.TOOL_SUCCEEDED: "工具成功",
    RunEventType.TOOL_FAILED: "工具失败",
    RunEventType.ARTIFACT_WRITTEN: "交付物已写入",
    RunEventType.QUALITY_CHECK_STARTED: "质量检查开始",
    RunEventType.QUALITY_CHECK_FAILED: "质量检查未通过",
    RunEventType.QUALITY_CHECK_PASSED: "质量检查通过",
    RunEventType.RESEARCH_SYNTHESIZED: "研究已综合",
    RunEventType.FINALIZING: "收尾中",
    RunEventType.RUN_SUCCEEDED: "任务成功",
    RunEventType.RUN_DEGRADED_SUCCESS: "降级成功",
    RunEventType.RUN_FAILED: "任务失败",
    RunEventType.RUN_CANCELLED: "任务已取消",
    RunEventType.RUN_TIMEOUT: "任务超时",
    RunEventType.STATE_CHANGED: "状态变更",
    RunEventType.CHECKPOINT_SAVED: "Checkpoint 已保存",
    RunEventType.WAL_REPLAY_STARTED: "WAL 重放开始",
    RunEventType.WAL_REPLAY_COMPLETED: "WAL 重放完成",
    RunEventType.CHECKPOINT_RESTORED: "Checkpoint 已恢复",
    RunEventType.MEMORY_COMPACTION_STARTED: "记忆压缩开始",
    RunEventType.MEMORY_COMPACTION_COMPLETED: "记忆压缩完成",
    RunEventType.QUALITY_REVISION_STARTED: "质量修订开始",
    RunEventType.QUALITY_CIRCUIT_BREAKER_TRIGGERED: "质量熔断",
}


TERMINAL_RUN_EVENT_TYPES: frozenset[RunEventType] = frozenset(
    {
        RunEventType.RUN_SUCCEEDED,
        RunEventType.RUN_DEGRADED_SUCCESS,
        RunEventType.RUN_FAILED,
        RunEventType.RUN_CANCELLED,
        RunEventType.RUN_TIMEOUT,
        RunEventType.QUALITY_CIRCUIT_BREAKER_TRIGGERED,
    }
)


class RunEvent(BaseModel):
    event_id: str = Field(alias="eventId")
    run_id: str = Field(alias="runId")
    timestamp: datetime
    type: RunEventType
    run_state: RunState = Field(alias="runState")
    label: str
    message: str
    description: str = ""
    iteration: int = 0
    tool: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

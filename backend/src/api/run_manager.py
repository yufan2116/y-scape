"""RunManager — Phase 1: lifecycle, state transitions, snapshot + WAL + checkpoint."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.agent_loop import AgentLoop
from src.agent.checkpoint import CheckpointData, CheckpointStore
from src.agent.runtime_state import (
    LoopOutcome,
    PlannerContext,
    RunRecord,
    RunState,
    TaskType,
    is_terminal,
    progress_for_state,
)
from src.agent.wal_replay import ReplayedRunState, replay_run
from src.demo.scenarios import get_scenario
from src.agent.deliverable_quality import DeliverableQualityGate, QualityBlockedError
from src.agent.research_memory import ResearchMemoryStore
from src.agent.report_writer import ReportWriter
from src.agent.synthesis_engine import SynthesisEngine
from src.agent.tools import ToolContext, ToolResult, default_tool_registry
from src.agent.wal import WalEventType, WalWriter
from src.api.event_bus import get_or_create_bus
from src.api.run_event import RunEventType
from src.api.status_snapshot import ArtifactMeta, RunStatusSnapshot, build_snapshot, snapshot_manager
from src.config import settings
from src.storage.artifact_manager import ArtifactManager
from src.storage.workspace import WorkspaceStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _terminal_event_type(state: RunState) -> RunEventType | None:
    mapping: dict[RunState, RunEventType] = {
        RunState.SUCCESS: RunEventType.RUN_SUCCEEDED,
        RunState.DEGRADED_SUCCESS: RunEventType.RUN_DEGRADED_SUCCESS,
        RunState.FAILED: RunEventType.RUN_FAILED,
        RunState.CANCELLED: RunEventType.RUN_CANCELLED,
        RunState.TIMEOUT: RunEventType.RUN_TIMEOUT,
        RunState.QUALITY_BLOCKED: RunEventType.QUALITY_CIRCUIT_BREAKER_TRIGGERED,
        RunState.STALE: RunEventType.RUN_FAILED,
        RunState.NEEDS_INPUT: RunEventType.RUN_FAILED,
        RunState.INTERRUPTED: RunEventType.RUN_CANCELLED,
    }
    return mapping.get(state)


class CancellationToken:
    """Cooperative cancellation — Phase 7 will use this instead of force-kill."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    async def wait(self) -> None:
        await self._event.wait()


class RunManager:
    """
    Phase 1–2: lifecycle, WAL, snapshot, events.
    Phase 4: Demo Mode + Agent Loop.
    Phase 7: Recovery retry / resume + WAL replay.
    """

    def __init__(self, runs_dir: Path | None = None) -> None:
        self.runs_dir = runs_dir or settings.runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, RunRecord] = {}
        self._cancel_tokens: dict[str, CancellationToken] = {}
        self._agent_tasks: dict[str, asyncio.Task] = {}
        self._demo_flags: dict[str, dict] = {}
        self._resume_context: dict[str, ReplayedRunState] = {}
        self._watchdog_task: asyncio.Task | None = None
        self._tool_registry = default_tool_registry
        self._agent_loop = AgentLoop(self)

    def _run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    @staticmethod
    def _resolve_demo_mode(demo_mode: bool | None) -> bool:
        if demo_mode is not None:
            return demo_mode
        if settings.demo_mode:
            return True
        if not settings.api_key_configured:
            return True
        return False

    def get_cancel_token(self, run_id: str) -> CancellationToken:
        if run_id not in self._cancel_tokens:
            self._cancel_tokens[run_id] = CancellationToken()
        return self._cancel_tokens[run_id]

    async def create_task(
        self,
        goal: str,
        *,
        demo_mode: bool | None = None,
        task_type: TaskType = TaskType.RESEARCH_REPORT,
        scenario: str | None = None,
    ) -> str:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run_dir = self._run_dir(run_id)
        for sub in ("workspace", "artifacts", "research_memory"):
            (run_dir / sub).mkdir(parents=True, exist_ok=True)

        now = _utcnow()
        effective_demo = self._resolve_demo_mode(demo_mode)
        record = RunRecord(
            run_id=run_id,
            goal=goal,
            task_type=task_type,
            demo_mode=effective_demo,
            scenario=scenario,
            run_state=RunState.CREATED,
            current_step="created",
            started_at=now,
            updated_at=now,
            heartbeat_at=now,
            planner_context=PlannerContext(goal=goal),
        )
        self._records[run_id] = record
        self._cancel_tokens[run_id] = CancellationToken()

        wal = WalWriter(run_dir, run_id)
        wal.append(
            WalEventType.RUN_CREATED,
            state_before=RunState.CREATED,
            state_after=RunState.CREATED,
            payload={"goal": goal, "demo_mode": effective_demo, "task_type": task_type.value},
        )

        self._sync_snapshot(record)
        self._persist_checkpoint(record)
        wal.append(
            WalEventType.SNAPSHOT_CREATED,
            state_after=RunState.CREATED,
            payload={"step": "run_created"},
        )

        bus = get_or_create_bus(run_id, run_dir)
        await bus.publish(
            RunEventType.RUN_STARTED,
            run_state=RunState.CREATED,
            message=f"任务已创建: {goal[:120]}",
            payload={"goal": goal, "demo_mode": effective_demo, "task_type": task_type.value},
        )
        await bus.publish(
            RunEventType.CHECKPOINT_SAVED,
            run_state=RunState.CREATED,
            message="Checkpoint 已保存",
            payload={"step": "run_created"},
        )
        return run_id

    async def create_demo_task(self, scenario_name: str, goal: str | None = None) -> str:
        scenario = get_scenario(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown demo scenario: {scenario_name}")
        task_type = TaskType(scenario.task_type)
        effective_goal = goal or scenario.goal
        run_id = await self.create_task(
            effective_goal,
            demo_mode=True,
            task_type=task_type,
            scenario=scenario_name,
        )
        flags: dict = {}
        if scenario_name == "recover_failed_tool_demo":
            flags["fail_search_once"] = True
        if scenario_name == "quality_failure_then_revision":
            flags["force_short_report"] = True
        self._demo_flags[run_id] = flags
        return run_id

    async def start_task(self, run_id: str) -> None:
        record = self._ensure_record(run_id)
        if is_terminal(record.run_state):
            raise ValueError(f"Cannot start terminal run {run_id}")
        if record.run_state in {RunState.INTERRUPTED, RunState.STALE, RunState.FAILED, RunState.QUALITY_BLOCKED}:
            raise ValueError(f"Run {run_id} must be resumed or retried before start (state={record.run_state.value})")
        existing = self._agent_tasks.get(run_id)
        if existing and not existing.done():
            return
        self.get_cancel_token(run_id)
        token = self._cancel_tokens[run_id]
        if token.is_cancelled:
            self._cancel_tokens[run_id] = CancellationToken()
        self._agent_tasks[run_id] = asyncio.create_task(self._run_agent_background(run_id))

    async def cancel_task(self, run_id: str) -> None:
        token = self.get_cancel_token(run_id)
        token.cancel()
        task = self._agent_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        record = self._records.get(run_id)
        if record and not is_terminal(record.run_state):
            await self.transition(
                run_id,
                RunState.CANCELLED,
                step="cancelled",
                stop_reason="user_cancel",
                thinking_message="用户取消任务",
            )

    async def _run_agent_background(self, run_id: str) -> None:
        try:
            await self._agent_loop.run(run_id)
        except asyncio.CancelledError:
            record = self._records.get(run_id)
            flags = self._demo_flags.get(run_id, {})
            if record and not is_terminal(record.run_state):
                if flags.pop("interrupt_requested", False):
                    await self.transition(
                        run_id,
                        RunState.INTERRUPTED,
                        step="interrupted",
                        stop_reason="task_interrupted",
                        thinking_message="Agent 被中断",
                    )
                else:
                    await self.transition(
                        run_id,
                        RunState.CANCELLED,
                        step="cancelled",
                        stop_reason="task_cancelled",
                    )
            raise
        finally:
            self._agent_tasks.pop(run_id, None)
            self._resume_context.pop(run_id, None)

    def get_replay_state(self, run_id: str) -> ReplayedRunState:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise ValueError(f"Run {run_id} not found")
        return replay_run(run_id, self.runs_dir)

    async def retry_task(self, run_id: str) -> None:
        run_dir = self._run_dir(run_id)
        replayed = replay_run(run_id, self.runs_dir)
        if not replayed.can_retry:
            raise ValueError(f"Run {run_id} cannot be retried (state={replayed.run_state.value})")

        record = self._hydrate_record_from_checkpoint(run_id)
        wal = WalWriter(run_dir, run_id)
        wal.append(
            WalEventType.RETRY_REQUESTED,
            state_before=record.run_state,
            state_after=RunState.RETRYING,
            payload={"retry_count": record.retry_count + 1},
        )

        record.retry_count += 1
        record.revision_attempt = 0
        record.error = None
        record.stop_reason = None
        record.finished_at = None
        if record.planner_context:
            record.planner_context.revision_attempt = 0
            record.planner_context.quality_failure_reasons = []

        flags = self._demo_flags.setdefault(run_id, {})
        flags.pop("force_short_report", None)
        flags.pop("quality_passed", None)
        flags.pop("report_written", None)

        await self.transition(
            run_id,
            RunState.RETRYING,
            step="retrying",
            thinking_message="用户请求重试",
        )
        self._cancel_tokens[run_id] = CancellationToken()
        await self.start_task(run_id)

    async def resume_task(self, run_id: str) -> None:
        run_dir = self._run_dir(run_id)
        replayed = replay_run(run_id, self.runs_dir)
        if not replayed.can_resume:
            raise ValueError(f"Run {run_id} cannot be resumed (state={replayed.run_state.value})")

        wal = WalWriter(run_dir, run_id)
        wal.append(
            WalEventType.WAL_REPLAY_STARTED,
            payload={"event_count": len(wal.read_all())},
        )
        wal.append(
            WalEventType.RESUME_REQUESTED,
            state_after=RunState.RECOVERING,
        )

        record = self._hydrate_record_from_checkpoint(run_id)
        record.revision_attempt = max(record.revision_attempt, replayed.revision_attempt)
        record.retry_count = replayed.retry_count
        record.error = replayed.last_error
        record.finished_at = None
        record.scenario = record.scenario or replayed.scenario
        self._records[run_id] = record

        await self._resolve_pending_on_resume(run_id, replayed)

        wal.append(
            WalEventType.CHECKPOINT_RESTORED,
            state_after=RunState.RECOVERING,
            payload={"step": record.current_step, "completed_steps": replayed.completed_steps},
        )
        await self.transition(
            run_id,
            RunState.RECOVERING,
            step="recovering",
            thinking_message="WAL 重放恢复运行",
        )

        self._apply_replay_flags(run_id, replayed)
        self._resume_context[run_id] = replayed
        self._cancel_tokens[run_id] = CancellationToken()

        wal.append(WalEventType.WAL_REPLAY_COMPLETED, state_after=RunState.RECOVERING)
        bus = get_or_create_bus(run_id, run_dir)
        await bus.publish(
            RunEventType.WAL_REPLAY_COMPLETED,
            run_state=RunState.RECOVERING,
            message="WAL 重放完成",
            payload={"completed_steps": replayed.completed_steps},
        )
        await bus.publish(
            RunEventType.CHECKPOINT_RESTORED,
            run_state=RunState.RECOVERING,
            message="Checkpoint 已恢复",
        )

        await self.start_task(run_id)

    async def interrupt_task(self, run_id: str) -> None:
        """Mark run as interrupted (simulated crash) — cooperative stop."""
        self._demo_flags.setdefault(run_id, {})["interrupt_requested"] = True
        self.get_cancel_token(run_id).cancel()
        task = self._agent_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        record = self._records.get(run_id)
        if record and record.run_state == RunState.INTERRUPTED:
            return
        if record and not is_terminal(record.run_state):
            await self.transition(
                run_id,
                RunState.INTERRUPTED,
                step="interrupted",
                stop_reason="simulated_interrupt",
                thinking_message="运行被中断（可 resume）",
            )

    def _hydrate_record_from_checkpoint(self, run_id: str) -> RunRecord:
        if run_id in self._records:
            return self._records[run_id]
        return self._ensure_record(run_id)

    def _apply_replay_flags(self, run_id: str, replayed: ReplayedRunState) -> None:
        flags = self._demo_flags.setdefault(run_id, {})
        steps = set(replayed.completed_steps)
        if "web_search" in steps or "tool:web_search" in steps:
            flags["search_ok"] = True
        if replayed.quality_passed or "quality_gate" in steps:
            flags["quality_passed"] = True
        if any(s.startswith("artifact:research_report") for s in steps):
            flags["report_written"] = True
        if "resume_quality_revision" in replayed.pending_actions:
            flags.pop("force_short_report", None)

    async def _resolve_pending_on_resume(self, run_id: str, replayed: ReplayedRunState) -> None:
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)

        if replayed.pending_tool:
            tool = replayed.pending_tool.get("tool", "unknown")
            status = replayed.pending_tool.get("status")
            if status == "started_incomplete":
                wal.append(
                    WalEventType.TOOL_FAILED,
                    payload={"tool": tool, "error": "recovery: incomplete tool marked failed"},
                )
                await bus.publish(
                    RunEventType.TOOL_FAILED,
                    run_state=RunState.RECOVERING,
                    message=f"恢复：未完成工具标记失败 {tool}",
                    tool=tool,
                    payload={"error": "recovery: incomplete tool"},
                )

        if replayed.pending_file_write:
            pw = replayed.pending_file_write
            staging = pw.get("staging_path")
            if staging and Path(staging).exists() and pw.get("status") == "staged":
                Path(staging).unlink(missing_ok=True)

    async def transition(
        self,
        run_id: str,
        new_state: RunState,
        *,
        step: str | None = None,
        current_tool: str | None = None,
        thinking_message: str | None = None,
        latest_reasoning: str | None = None,
        latest_tool_result: dict[str, Any] | None = None,
        error: str | None = None,
        stop_reason: str | None = None,
        progress: float | None = None,
        wal_event: WalEventType = WalEventType.STATE_CHANGED,
        wal_payload: dict[str, Any] | None = None,
    ) -> RunStatusSnapshot:
        record = self._ensure_record(run_id)
        state_before = record.run_state
        if is_terminal(state_before) and new_state not in {RunState.RECOVERING, RunState.RETRYING}:
            raise ValueError(f"Cannot transition from terminal state {state_before.value}")

        record.run_state = new_state
        record.current_step = step or new_state.value
        record.updated_at = _utcnow()
        record.heartbeat_at = record.updated_at
        if current_tool is not None:
            record.current_tool = current_tool
        if thinking_message is not None:
            record.thinking_message = thinking_message
        if latest_reasoning is not None:
            record.latest_reasoning = latest_reasoning
        if latest_tool_result is not None:
            record.latest_tool_result = latest_tool_result
        if error is not None:
            record.error = error
        if stop_reason is not None:
            record.stop_reason = stop_reason
        record.progress = progress if progress is not None else progress_for_state(new_state)

        if is_terminal(new_state):
            record.finished_at = record.updated_at

        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        wal.append(
            wal_event,
            state_before=state_before,
            state_after=new_state,
            payload=wal_payload or {"step": record.current_step},
        )

        snapshot = self._sync_snapshot(record)
        self._persist_checkpoint(record)
        wal.append(
            WalEventType.SNAPSHOT_CREATED,
            state_after=new_state,
            payload={"step": record.current_step},
        )

        await self._publish_timeline_events(
            run_id,
            record,
            state_before=state_before,
            new_state=new_state,
            thinking_message=thinking_message,
        )
        return snapshot

    async def touch_heartbeat(self, run_id: str) -> None:
        record = self._require_record(run_id)
        record.heartbeat_at = _utcnow()
        self._sync_snapshot(record)

    def get_status(self, run_id: str) -> RunStatusSnapshot | None:
        """Hot path: memory only. Cold load only when record exists on disk but not in memory."""
        snap = snapshot_manager.get(run_id)
        if snap:
            return snap
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return None
        return snapshot_manager.load_cold(run_id, run_dir)

    def get_record(self, run_id: str) -> RunRecord | None:
        return self._records.get(run_id)

    def get_events(self, run_id: str, *, after_event_id: str | None = None, limit: int = 200):
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return []
        bus = get_or_create_bus(run_id, run_dir)
        return bus.after_event_id(after_event_id, limit=limit)

    def get_audit_log(self, run_id: str) -> list[dict]:
        """Layer B — audit log (mirrors WAL). Not for Timeline UI."""
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        return [e.model_dump(by_alias=True, mode="json") for e in wal.read_audit_all()]

    def get_wal(self, run_id: str) -> list[dict]:
        """WAL for recovery — not for Timeline UI."""
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        return [e.model_dump(by_alias=True, mode="json") for e in wal.read_all()]

    def is_terminal(self, run_id: str) -> bool:
        snap = self.get_status(run_id)
        return snap is not None and is_terminal(snap.run_state)

    async def execute_tool(
        self,
        run_id: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        Unified tool pipeline:
        TOOL_INTENT → TOOL_STARTED → execute → TOOL_COMMITTED|FAILED
        → snapshot → timeline → checkpoint
        """
        record = self._ensure_record(run_id)
        if is_terminal(record.run_state):
            return ToolResult(ok=False, tool=tool_name, output={}, error="run is terminal")

        token = self.get_cancel_token(run_id)
        if token.is_cancelled:
            return ToolResult(ok=False, tool=tool_name, output={}, error="cancelled")

        params = params or {}
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)

        if not self._tool_registry.has(tool_name):
            return ToolResult(ok=False, tool=tool_name, output={}, error=f"Unknown tool: {tool_name}")

        if tool_name == "file_write":
            fname = params.get("path") or params.get("name", "")
            if fname == "research_report.md" and record.task_type == TaskType.RESEARCH_REPORT:
                memory = ResearchMemoryStore(run_dir)
                if not memory.has_synthesis():
                    return ToolResult(
                        ok=False,
                        tool=tool_name,
                        output={},
                        error="research_report.md requires synthesis pipeline (Phase 5)",
                    )

        state_before = record.run_state
        record.run_state = RunState.TOOL_PENDING
        record.current_tool = tool_name
        record.current_step = "tool_pending"
        self._sync_snapshot(record)

        wal.append(
            WalEventType.TOOL_INTENT,
            state_before=state_before,
            state_after=RunState.TOOL_PENDING,
            payload={"tool": tool_name, "params": params},
        )
        wal.append(
            WalEventType.TOOL_STARTED,
            state_before=RunState.TOOL_PENDING,
            state_after=RunState.TOOL_RUNNING,
            payload={"tool": tool_name},
        )

        record.run_state = RunState.TOOL_RUNNING
        record.current_step = "tool_running"
        self._sync_snapshot(record)

        await bus.publish(
            RunEventType.TOOL_STARTED,
            run_state=RunState.TOOL_RUNNING,
            message=f"工具开始: {tool_name}",
            tool=tool_name,
            payload=params,
        )

        ctx = ToolContext(
            run_id=run_id,
            run_dir=run_dir,
            goal=record.goal,
            workspace=WorkspaceStore(run_dir),
        )

        try:
            result = await self._tool_registry.execute(tool_name, params, ctx)
        except asyncio.CancelledError:
            wal.append(
                WalEventType.TOOL_FAILED,
                state_after=RunState.TOOL_FAILED,
                payload={"tool": tool_name, "error": "cancelled"},
            )
            await bus.publish(
                RunEventType.TOOL_FAILED,
                run_state=RunState.TOOL_FAILED,
                message=f"工具取消: {tool_name}",
                tool=tool_name,
                payload={"error": "cancelled"},
            )
            record.run_state = RunState.TOOL_FAILED
            record.current_tool = None
            self._sync_snapshot(record)
            self._persist_checkpoint(record)
            raise

        if result.ok:
            wal.append(
                WalEventType.TOOL_COMMITTED,
                state_after=RunState.TOOL_SUCCESS,
                payload={"tool": tool_name, "output_preview": str(result.output)[:300]},
            )
            record.run_state = RunState.TOOL_SUCCESS
            record.latest_tool_result = result.to_dict()
            if record.planner_context:
                record.planner_context.committed_tool_results.append(result.to_dict())

            await bus.publish(
                RunEventType.TOOL_SUCCEEDED,
                run_state=RunState.TOOL_SUCCESS,
                message=f"工具成功: {tool_name}",
                tool=tool_name,
                payload=result.output,
            )

            if tool_name == "file_write" and params.get("to_artifact"):
                filename = params.get("path") or params.get("name", "output.md")
                content = params.get("content", "")
                artifact_type = params.get("artifact_type", "file")
                meta = ArtifactManager(run_dir, run_id, wal).write_artifact(
                    filename, content, artifact_type=artifact_type
                )
                self._register_artifact_meta(record, meta)
                await bus.publish(
                    RunEventType.ARTIFACT_WRITTEN,
                    run_state=RunState.TOOL_SUCCESS,
                    message=f"交付物已写入: {filename}",
                    payload={"name": meta.name, "size": meta.size},
                )

            record.run_state = RunState.THINKING
        else:
            wal.append(
                WalEventType.TOOL_FAILED,
                state_after=RunState.TOOL_FAILED,
                payload={"tool": tool_name, "error": result.error},
            )
            record.run_state = RunState.TOOL_FAILED
            record.error = result.error
            record.latest_tool_result = result.to_dict()
            await bus.publish(
                RunEventType.TOOL_FAILED,
                run_state=RunState.TOOL_FAILED,
                message=f"工具失败: {tool_name}",
                tool=tool_name,
                payload={"error": result.error},
            )
            record.run_state = RunState.THINKING

        record.current_tool = None
        record.current_step = "tool_complete"
        record.heartbeat_at = _utcnow()
        self._sync_snapshot(record)
        self._persist_checkpoint(record)
        wal.append(
            WalEventType.SNAPSHOT_CREATED,
            state_after=record.run_state,
            payload={"step": "tool_complete", "tool": tool_name},
        )
        await bus.publish(
            RunEventType.CHECKPOINT_SAVED,
            run_state=record.run_state,
            message="Checkpoint 已保存",
            payload={"step": "tool_complete"},
        )
        return result

    async def write_artifact(
        self,
        run_id: str,
        filename: str,
        content: str,
        *,
        artifact_type: str = "report",
    ) -> ArtifactMeta:
        """Direct artifact write API — WAL + timeline, independent of tool name."""
        record = self._ensure_record(run_id)
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)

        record.run_state = RunState.WRITING_ARTIFACT
        record.current_step = "writing_artifact"
        self._sync_snapshot(record)

        meta = ArtifactManager(run_dir, run_id, wal).write_artifact(
            filename, content, artifact_type=artifact_type
        )
        self._register_artifact_meta(record, meta)

        record.run_state = RunState.THINKING
        self._sync_snapshot(record)
        self._persist_checkpoint(record)

        await bus.publish(
            RunEventType.ARTIFACT_WRITTEN,
            run_state=record.run_state,
            message=f"交付物已写入: {filename}",
            payload={"name": meta.name, "size": meta.size},
        )
        await bus.publish(
            RunEventType.CHECKPOINT_SAVED,
            run_state=record.run_state,
            message="Checkpoint 已保存",
            payload={"step": "artifact_written"},
        )
        return meta

    async def synthesize_and_write_report(
        self,
        run_id: str,
        filename: str = "research_report.md",
    ) -> ArtifactMeta:
        """
        Research pipeline: Memory → Synthesis → ReportWriter → artifact → QualityGate.
        """
        record = self._ensure_record(run_id)
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)
        memory = ResearchMemoryStore(run_dir)

        if not memory.has_raw_evidence():
            raise ValueError("No raw evidence for synthesis")

        wal.append(
            WalEventType.RESEARCH_SYNTHESIS_STARTED,
            state_before=record.run_state,
            state_after=RunState.SYNTHESIZING_RESEARCH,
            payload={"filename": filename},
        )
        await self.transition(
            run_id,
            RunState.SYNTHESIZING_RESEARCH,
            step="synthesizing",
            thinking_message="ResearchMemory → SynthesisEngine",
        )

        findings = memory.ensure_findings()
        wal.append(
            WalEventType.RESEARCH_FINDINGS_EXTRACTED,
            state_after=RunState.SYNTHESIZING_RESEARCH,
            payload={"count": len(findings)},
        )

        engine = SynthesisEngine(demo_mode=record.demo_mode)
        synthesis = await engine.synthesize(memory, goal=record.goal)

        wal.append(
            WalEventType.RESEARCH_SYNTHESIS_COMMITTED,
            state_after=RunState.SYNTHESIZING_RESEARCH,
            payload={
                "trends": len(synthesis.key_trends),
                "sources": len(synthesis.sources),
            },
        )
        await bus.publish(
            RunEventType.RESEARCH_SYNTHESIZED,
            run_state=RunState.SYNTHESIZING_RESEARCH,
            message="研究综合完成",
            payload={"findings": len(findings), "sources": len(synthesis.sources)},
        )

        demo_flags = self._demo_flags.setdefault(run_id, {})
        force_short = demo_flags.get("force_short_report", False)
        source_ids = [f.source for f in findings]
        max_attempts = settings.max_quality_failures
        writer = ReportWriter()
        last_meta: ArtifactMeta | None = None

        for attempt in range(max_attempts):
            use_short = force_short and record.revision_attempt == 0 and attempt == 0
            content = writer.write(synthesis, goal=record.goal, force_short=use_short)
            last_meta = await self.write_artifact(run_id, filename, content, artifact_type="report")

            passed = await self._run_quality_gate(
                run_id,
                filename=filename,
                content=content,
                source_ids=source_ids,
            )
            if passed:
                demo_flags.pop("force_short_report", None)
                demo_flags["quality_passed"] = True
                return last_meta

            record.revision_attempt += 1
            if record.planner_context is not None:
                record.planner_context.revision_attempt = record.revision_attempt

            if record.revision_attempt >= settings.max_quality_failures:
                wal.append(
                    WalEventType.QUALITY_CIRCUIT_BREAKER_TRIGGERED,
                    state_before=record.run_state,
                    state_after=RunState.QUALITY_BLOCKED,
                    payload={"revision_attempt": record.revision_attempt},
                )
                await self.transition(
                    run_id,
                    RunState.QUALITY_BLOCKED,
                    step="quality_blocked",
                    stop_reason="max_quality_failures",
                    thinking_message="质量熔断：超过最大修订次数",
                )
                raise QualityBlockedError("Quality circuit breaker triggered")

            wal.append(
                WalEventType.QUALITY_REVISION_STARTED,
                state_after=RunState.QUALITY_REVISION,
                payload={"attempt": record.revision_attempt},
            )
            await self.transition(
                run_id,
                RunState.QUALITY_REVISION,
                step="quality_revision",
                thinking_message=f"质量修订第 {record.revision_attempt} 次",
            )
            await bus.publish(
                RunEventType.QUALITY_REVISION_STARTED,
                run_state=RunState.QUALITY_REVISION,
                message=f"质量修订第 {record.revision_attempt} 次",
                payload={"attempt": record.revision_attempt},
            )
            demo_flags["force_short_report"] = False

        raise QualityBlockedError("Quality gate exhausted attempts")

    async def _run_quality_gate(
        self,
        run_id: str,
        *,
        filename: str,
        content: str,
        source_ids: list[str],
    ) -> bool:
        record = self._ensure_record(run_id)
        run_dir = self._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)

        gate = DeliverableQualityGate.for_task(
            record.task_type if isinstance(record.task_type, TaskType) else TaskType(record.task_type)
        )

        wal.append(
            WalEventType.QUALITY_CHECK_STARTED,
            state_before=record.run_state,
            payload={"filename": filename},
        )
        await bus.publish(
            RunEventType.QUALITY_CHECK_STARTED,
            run_state=record.run_state,
            message=f"质量检查: {filename}",
            payload={"filename": filename},
        )

        result = gate.validate(content, source_ids=source_ids, filename=filename)

        if result.passed:
            wal.append(
                WalEventType.QUALITY_CHECK_PASSED,
                state_after=record.run_state,
                payload=result.model_dump(),
            )
            await bus.publish(
                RunEventType.QUALITY_CHECK_PASSED,
                run_state=record.run_state,
                message="质量检查通过",
                payload=result.model_dump(),
            )
            self._sync_snapshot(record)
            self._persist_checkpoint(record)
            return True

        failures = result.failures
        if record.planner_context is not None:
            record.planner_context.quality_failure_reasons.extend(failures)

        wal.append(
            WalEventType.QUALITY_CHECK_FAILED,
            state_after=record.run_state,
            payload={"failures": failures, "revision_attempt": record.revision_attempt + 1},
        )
        await bus.publish(
            RunEventType.QUALITY_CHECK_FAILED,
            run_state=record.run_state,
            message="质量检查未通过",
            payload={"failures": failures},
        )
        record.error = "; ".join(failures)
        self._sync_snapshot(record)
        self._persist_checkpoint(record)
        return False

    def get_artifact_content(self, run_id: str, filename: str) -> str:
        """Independent preview — reads file only, no status/log join."""
        run_dir = self._run_dir(run_id)
        if not (run_dir / "artifacts" / filename).exists():
            raise FileNotFoundError(filename)
        return ArtifactManager(run_dir, run_id, WalWriter(run_dir, run_id)).read_artifact(filename)

    def list_artifacts(self, run_id: str) -> list[ArtifactMeta]:
        record = self._records.get(run_id)
        if record and record.artifacts_meta:
            return self._artifact_meta_from_record(record)
        self._ensure_record(run_id)
        record = self._records.get(run_id)
        if record:
            return self._artifact_meta_from_record(record)
        return []

    def _register_artifact_meta(self, record: RunRecord, meta: ArtifactMeta) -> None:
        entry = meta.model_dump(by_alias=True, mode="json")
        record.artifacts_meta = [
            a for a in record.artifacts_meta if a.get("name") != meta.name
        ]
        record.artifacts_meta.append(entry)

    def _ensure_record(self, run_id: str) -> RunRecord:
        if run_id in self._records:
            return self._records[run_id]
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            raise ValueError(f"Run {run_id} not found")
        cp = CheckpointStore(run_dir).load()
        if not cp:
            raise ValueError(f"Run {run_id} not found")
        record = RunRecord(
            run_id=cp.run_id,
            goal=cp.goal,
            task_type=cp.task_type,
            demo_mode=cp.demo_mode,
            scenario=cp.scenario,
            run_state=cp.run_state,
            iteration=cp.iteration,
            revision_attempt=cp.revision_attempt,
            retry_count=cp.retry_count,
            stop_reason=cp.stop_reason,
            error=cp.error,
            current_step=cp.current_step,
            progress=cp.progress,
            artifacts_meta=list(cp.artifacts),
            started_at=cp.started_at,
            updated_at=cp.updated_at,
            finished_at=cp.finished_at,
            heartbeat_at=cp.updated_at,
            planner_context=cp.planner_context,
        )
        self._records[run_id] = record
        if run_id not in self._cancel_tokens:
            self._cancel_tokens[run_id] = CancellationToken()
        get_or_create_bus(run_id, run_dir)
        return record

    async def _publish_timeline_events(
        self,
        run_id: str,
        record: RunRecord,
        *,
        state_before: RunState,
        new_state: RunState,
        thinking_message: str | None,
    ) -> None:
        bus = get_or_create_bus(run_id, self._run_dir(run_id))
        msg = thinking_message or f"{state_before.value} → {new_state.value}"
        await bus.publish(
            RunEventType.STATE_CHANGED,
            run_state=new_state,
            message=msg,
            payload={"from": state_before.value, "to": new_state.value, "step": record.current_step},
        )
        await bus.publish(
            RunEventType.CHECKPOINT_SAVED,
            run_state=new_state,
            message="Checkpoint 已保存",
            payload={"step": record.current_step},
        )
        terminal_type = _terminal_event_type(new_state)
        if terminal_type:
            await bus.publish(
                terminal_type,
                run_state=new_state,
                message=msg,
                payload={"stop_reason": record.stop_reason, "error": record.error},
            )
        if is_terminal(new_state):
            await bus.close_subscribers()

    async def start_watchdog(self) -> None:
        if self._watchdog_task and not self._watchdog_task.done():
            return
        self._watchdog_task = asyncio.create_task(self._stale_watchdog_loop())

    async def stop_watchdog(self) -> None:
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass

    async def _stale_watchdog_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            now = _utcnow()
            threshold = settings.stale_threshold_seconds
            for run_id, record in list(self._records.items()):
                if is_terminal(record.run_state):
                    continue
                elapsed = (now - record.heartbeat_at).total_seconds()
                if elapsed > threshold and record.run_state != RunState.STALE:
                    await self.transition(
                        run_id,
                        RunState.STALE,
                        step="stale_watchdog",
                        stop_reason="heartbeat_timeout",
                        wal_payload={"elapsed_seconds": elapsed},
                    )

    def _sync_snapshot(self, record: RunRecord) -> RunStatusSnapshot:
        snap = build_snapshot(
            run_id=record.run_id,
            goal=record.goal,
            run_state=record.run_state,
            progress=record.progress,
            current_step=record.current_step,
            current_tool=record.current_tool,
            thinking_message=record.thinking_message,
            latest_reasoning=record.latest_reasoning,
            latest_tool_result=record.latest_tool_result,
            artifacts=self._artifact_meta_from_record(record),
            error=record.error,
            stop_reason=record.stop_reason,
            revision_attempt=record.revision_attempt,
            iteration=record.iteration,
            demo_mode=record.demo_mode,
            task_type=record.task_type.value if isinstance(record.task_type, TaskType) else str(record.task_type),
            started_at=record.started_at,
            finished_at=record.finished_at,
            heartbeat_at=record.heartbeat_at,
        )
        snapshot_manager.upsert(snap, self._run_dir(record.run_id))
        return snap

    def _persist_checkpoint(self, record: RunRecord) -> None:
        data = CheckpointData(
            run_id=record.run_id,
            goal=record.goal,
            task_type=record.task_type if isinstance(record.task_type, TaskType) else TaskType(record.task_type),
            demo_mode=record.demo_mode,
            scenario=record.scenario,
            run_state=record.run_state,
            iteration=record.iteration,
            revision_attempt=record.revision_attempt,
            retry_count=record.retry_count,
            stop_reason=record.stop_reason,
            error=record.error,
            progress=record.progress,
            current_step=record.current_step,
            artifacts=record.artifacts_meta,
            planner_context=record.planner_context,
            started_at=record.started_at,
            updated_at=record.updated_at,
            finished_at=record.finished_at,
        )
        CheckpointStore(self._run_dir(record.run_id)).save(data)

    def _artifact_meta_from_record(self, record: RunRecord) -> list[ArtifactMeta]:
        # Phase 1: metadata from in-memory record only — status path never scans disk
        items: list[ArtifactMeta] = []
        for a in record.artifacts_meta:
            created = a.get("createdAt")
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created)
            elif isinstance(created, datetime):
                created_dt = created
            else:
                created_dt = _utcnow()
            items.append(
                ArtifactMeta(
                    name=a["name"],
                    type=a.get("type", "file"),
                    path=a["path"],
                    url=a.get("url", ""),
                    size=a.get("size", 0),
                    createdAt=created_dt,
                )
            )
        return items

    def _require_record(self, run_id: str) -> RunRecord:
        return self._ensure_record(run_id)


run_manager = RunManager()

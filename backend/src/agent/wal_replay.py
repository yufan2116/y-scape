"""WAL replay — reconstruct run state from disk (Phase 7)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from src.agent.checkpoint import CheckpointStore
from src.agent.runtime_state import RunState
from src.agent.wal import WalEvent, WalEventType, WalWriter
from src.config import settings


class ReplayedRunState(BaseModel):
    run_id: str
    run_state: RunState
    goal: str = ""
    demo_mode: bool = False
    scenario: str | None = None
    task_type: str = "research_report"
    revision_attempt: int = 0
    retry_count: int = 0
    completed_steps: list[str] = Field(default_factory=list)
    pending_tool: dict | None = None
    pending_file_write: dict | None = None
    can_resume: bool = False
    can_retry: bool = False
    last_error: str | None = None
    quality_passed: bool = False
    pending_actions: list[str] = Field(default_factory=list)


RETRYABLE_STATES = frozenset(
    {
        RunState.FAILED,
        RunState.TIMEOUT,
        RunState.QUALITY_BLOCKED,
        RunState.STALE,
        RunState.INTERRUPTED,
    }
)

RESUMABLE_STATES = frozenset(
    {
        RunState.STALE,
        RunState.INTERRUPTED,
        RunState.FAILED,
        RunState.THINKING,
        RunState.PLANNING,
        RunState.TOOL_RUNNING,
        RunState.TOOL_PENDING,
        RunState.SYNTHESIZING_RESEARCH,
        RunState.QUALITY_REVISION,
        RunState.WRITING_ARTIFACT,
        RunState.RECOVERING,
    }
)


class WalReplayEngine:
    """Replay wal.jsonl to derive recovery context without reading Timeline logs."""

    @classmethod
    def replay(cls, run_dir: Path, run_id: str | None = None) -> ReplayedRunState:
        rid = run_id or run_dir.name
        wal = WalWriter(run_dir, rid)
        events = wal.read_all()
        if not events:
            raise ValueError(f"No WAL events for run {rid}")
        return cls._replay_events(rid, run_dir, events)

    @classmethod
    def _replay_events(cls, run_id: str, run_dir: Path, events: list[WalEvent]) -> ReplayedRunState:
        state = RunState.CREATED
        goal = ""
        demo_mode = False
        scenario: str | None = None
        task_type = "research_report"
        revision_attempt = 0
        retry_count = 0
        last_error: str | None = None
        completed: set[str] = set()
        open_tools: dict[str, dict] = {}
        open_writes: dict[str, dict] = {}
        quality_passed = False
        pending_actions: list[str] = []

        for event in events:
            if event.state_after:
                state = event.state_after

            payload = event.payload
            et = event.type

            if et == WalEventType.RUN_CREATED:
                goal = payload.get("goal", goal)
                demo_mode = payload.get("demo_mode", demo_mode)
                scenario = payload.get("scenario", scenario)
                task_type = payload.get("task_type", task_type)
                completed.add("created")

            elif et == WalEventType.TOOL_INTENT:
                tool = payload.get("tool", "unknown")
                open_tools[tool] = {
                    "tool": tool,
                    "status": "intent_only",
                    "params": payload.get("params", {}),
                }

            elif et == WalEventType.TOOL_STARTED:
                tool = payload.get("tool", "unknown")
                if tool in open_tools:
                    open_tools[tool]["status"] = "started_incomplete"

            elif et == WalEventType.TOOL_COMMITTED:
                tool = payload.get("tool", "unknown")
                open_tools.pop(tool, None)
                completed.add(f"tool:{tool}")
                if tool == "web_search":
                    completed.add("web_search")

            elif et == WalEventType.TOOL_FAILED:
                tool = payload.get("tool", "unknown")
                open_tools.pop(tool, None)
                last_error = payload.get("error")

            elif et == WalEventType.RESEARCH_FINDINGS_EXTRACTED:
                completed.add("findings_extracted")

            elif et == WalEventType.RESEARCH_SYNTHESIS_COMMITTED:
                completed.add("synthesis_committed")

            elif et == WalEventType.FILE_WRITE_INTENT:
                name = payload.get("filename") or payload.get("name", "unknown")
                open_writes[name] = {"filename": name, "status": "intent_only"}

            elif et == WalEventType.FILE_WRITE_STAGED:
                name = payload.get("filename") or payload.get("name", "unknown")
                if name in open_writes:
                    open_writes[name]["status"] = "staged"
                    open_writes[name]["staging_path"] = payload.get("staging_path")

            elif et == WalEventType.FILE_WRITE_COMMITTED:
                name = payload.get("filename") or payload.get("name", "unknown")
                open_writes.pop(name, None)
                completed.add(f"artifact:{name}")

            elif et == WalEventType.ARTIFACT_REGISTERED:
                name = payload.get("name", "unknown")
                completed.add(f"artifact:{name}")

            elif et == WalEventType.QUALITY_CHECK_FAILED:
                revision_attempt = max(
                    revision_attempt,
                    int(payload.get("revision_attempt", revision_attempt + 1)),
                )
                if revision_attempt == 0:
                    revision_attempt += 1
                failures = payload.get("failures", [])
                if failures:
                    last_error = "; ".join(failures)

            elif et == WalEventType.QUALITY_CHECK_PASSED:
                quality_passed = True
                completed.add("quality_gate")

            elif et == WalEventType.FINALIZE_COMMITTED:
                completed.add("finalize")

            elif et == WalEventType.RETRY_REQUESTED:
                retry_count += 1

            elif et == WalEventType.RESUME_REQUESTED:
                completed.add("resume_requested")

        pending_tool = None
        if open_tools:
            _tool, info = next(iter(open_tools.items()))
            pending_tool = info
            pending_actions.append(f"resolve_pending_tool:{_tool}")

        pending_file_write = None
        if open_writes:
            _name, info = next(iter(open_writes.items()))
            staging = info.get("staging_path")
            pending_file_write = {
                **info,
                "staged_file_exists": bool(staging and Path(staging).exists()),
            }
            pending_actions.append(f"resolve_pending_file_write:{_name}")

        evidence_path = run_dir / "research_memory" / "raw_evidence.jsonl"
        if evidence_path.exists() and evidence_path.read_text(encoding="utf-8").strip():
            completed.add("web_search")

        synthesis_path = run_dir / "research_memory" / "synthesis_result.json"
        if synthesis_path.exists():
            completed.add("synthesis_committed")

        cp = CheckpointStore(run_dir).load()
        if cp:
            revision_attempt = max(revision_attempt, cp.revision_attempt)
            if cp.scenario:
                scenario = cp.scenario

        can_retry = state in RETRYABLE_STATES
        can_resume = state in RESUMABLE_STATES and state not in {
            RunState.SUCCESS,
            RunState.CANCELLED,
            RunState.DEGRADED_SUCCESS,
            RunState.QUALITY_BLOCKED,
        }
        if state == RunState.FAILED:
            can_resume = revision_attempt > 0 or bool(completed - {"created"})
        if state == RunState.QUALITY_BLOCKED:
            can_resume = False
            can_retry = True
        if state in {RunState.SUCCESS, RunState.CANCELLED, RunState.DEGRADED_SUCCESS}:
            can_resume = False
            can_retry = False
        if revision_attempt > 0 and not quality_passed and state not in {
            RunState.SUCCESS,
            RunState.CANCELLED,
        }:
            can_resume = True
            if "resume_quality_revision" not in pending_actions:
                pending_actions.append("resume_quality_revision")

        return ReplayedRunState(
            run_id=run_id,
            run_state=state,
            goal=goal,
            demo_mode=demo_mode,
            scenario=scenario,
            task_type=task_type,
            revision_attempt=revision_attempt,
            retry_count=retry_count,
            completed_steps=sorted(completed),
            pending_tool=pending_tool,
            pending_file_write=pending_file_write,
            can_resume=can_resume,
            can_retry=can_retry,
            last_error=last_error,
            quality_passed=quality_passed,
            pending_actions=pending_actions,
        )


def replay_run(run_id: str, runs_dir: Path | None = None) -> ReplayedRunState:
    base = runs_dir or settings.runs_dir
    run_dir = base / run_id
    if not run_dir.exists():
        raise ValueError(f"Run {run_id} not found")
    return WalReplayEngine.replay(run_dir, run_id)

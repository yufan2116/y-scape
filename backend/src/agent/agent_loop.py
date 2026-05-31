"""Agent loop — bounded iterations, Demo Mode (Phase 4)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from src.agent.deliverable_quality import QualityBlockedError
from src.agent.planner import Planner
from src.agent.research_memory import ResearchMemoryStore
from src.agent.runtime_state import LoopOutcome, RunState, TaskType, is_terminal
from src.agent.tools import ToolResult
from src.agent.wal import WalEventType, WalWriter
from src.api.event_bus import get_or_create_bus
from src.api.run_event import RunEventType
from src.config import settings
from src.integrations.deepseek_client import DeepSeekError

if TYPE_CHECKING:
    from src.api.run_manager import RunManager


class AgentLoop:
    def __init__(self, manager: "RunManager") -> None:
        self.manager = manager

    async def run(self, run_id: str) -> LoopOutcome:
        record = self.manager._ensure_record(run_id)
        run_dir = self.manager._run_dir(run_id)
        planner = Planner(demo_mode=record.demo_mode, scenario=record.scenario)
        get_or_create_bus(run_id, run_dir)

        await self.manager.transition(
            run_id,
            RunState.PLANNING,
            step="planning",
            thinking_message="Agent loop 启动",
        )

        outcome = LoopOutcome.CONTINUE
        try:
            outcome = await asyncio.wait_for(
                self._iterations(run_id, record, planner, run_dir),
                timeout=settings.agent_loop_timeout_seconds,
            )
        except asyncio.TimeoutError:
            outcome = LoopOutcome.TIMEOUT
        except asyncio.CancelledError:
            token = self.manager.get_cancel_token(run_id)
            outcome = LoopOutcome.CANCELLED if token.is_cancelled else LoopOutcome.FAILED
            raise

        await self._finalize_outcome(run_id, outcome)
        return outcome

    async def _iterations(self, run_id: str, record, planner: Planner, run_dir: Path) -> LoopOutcome:
        token = self.manager.get_cancel_token(run_id)
        bus = get_or_create_bus(run_id, run_dir)

        while record.iteration < settings.max_iterations:
            if token.is_cancelled:
                return LoopOutcome.CANCELLED

            record.iteration += 1
            from src.api.run_manager import _utcnow

            record.heartbeat_at = _utcnow()
            self.manager._sync_snapshot(record)

            ctx = self._build_ctx(run_id, record, run_dir)
            await bus.publish(
                RunEventType.PLANNER_STARTED,
                run_state=RunState.PLANNING,
                message="规划器启动",
                iteration=record.iteration,
            )

            try:
                plan = await planner.plan(goal=record.goal, iteration=record.iteration, ctx=ctx)
            except asyncio.TimeoutError:
                return LoopOutcome.TIMEOUT
            except DeepSeekError as exc:
                record.error = str(exc)
                return LoopOutcome.FAILED
            except Exception as exc:
                record.error = str(exc)
                return LoopOutcome.FAILED

            await bus.publish(
                RunEventType.PLANNER_RESPONSE,
                run_state=RunState.THINKING,
                message=plan.get("reasoning", ""),
                iteration=record.iteration,
                payload=plan,
            )
            await self.manager.transition(
                run_id,
                RunState.THINKING,
                step="thinking",
                thinking_message=plan.get("reasoning"),
            )

            action = plan.get("action")

            if action == "tool":
                tool = plan.get("tool", "")
                params = plan.get("params", {})
                if (
                    record.scenario == "recover_failed_tool_demo"
                    and tool == "web_search"
                ):
                    demo = self.manager._demo_flags.get(run_id, {})
                    if demo.get("fail_search_once") and not demo.get("search_failed_once"):
                        demo["search_failed_once"] = True
                        result = await self._simulate_tool_fail(run_id, tool, "demo: simulated tool failure")
                    else:
                        result = await self.manager.execute_tool(run_id, tool, params)
                else:
                    result = await self.manager.execute_tool(run_id, tool, params)

                if not result.ok:
                    if record.scenario == "recover_failed_tool_demo" and tool == "web_search":
                        continue
                    return LoopOutcome.FAILED
                if tool == "web_search":
                    self.manager._demo_flags.setdefault(run_id, {})["search_ok"] = True
                if tool == "pdf_extract":
                    self.manager._demo_flags.setdefault(run_id, {})["pdf_extracted"] = True
                if tool == "finish_task":
                    self.manager._demo_flags.setdefault(run_id, {})["finish_task_called"] = True
                continue

            if action in ("synthesize_report", "demo_synthesize_report"):
                if not ctx.get("has_evidence"):
                    return LoopOutcome.FAILED
                filename = plan.get("filename", "research_report.md")
                try:
                    await self.manager.synthesize_and_write_report(run_id, filename)
                except QualityBlockedError:
                    return LoopOutcome.FAILED
                except ValueError as exc:
                    record.error = str(exc)
                    return LoopOutcome.FAILED
                self.manager._demo_flags.setdefault(run_id, {})["report_written"] = True
                self.manager._demo_flags[run_id]["quality_passed"] = True
                continue

            if action == "slow_step":
                seconds = float(plan.get("seconds", 2))
                for _ in range(int(seconds * 2)):
                    if token.is_cancelled:
                        return LoopOutcome.CANCELLED
                    await asyncio.sleep(0.5)
                self.manager._demo_flags.setdefault(run_id, {})["slow_step_done"] = True
                continue

            if action == "needs_input":
                await self.manager.transition(
                    run_id,
                    RunState.NEEDS_INPUT,
                    step="needs_input",
                    thinking_message=plan.get("message", "needs input"),
                    stop_reason="missing_input",
                )
                return LoopOutcome.NEEDS_INPUT

            if action == "finish":
                finish_flags = self.manager._demo_flags.get(run_id, {})
                artifact_names = {a.get("name") for a in record.artifacts_meta}
                if (
                    record.task_type == TaskType.RESEARCH_REPORT
                    and "research_report.md" in artifact_names
                    and not finish_flags.get("quality_passed")
                ):
                    return LoopOutcome.FAILED
                return LoopOutcome.SUCCESS

            if action == "cancelled":
                return LoopOutcome.CANCELLED

            return LoopOutcome.FAILED

        return LoopOutcome.FAILED

    async def _simulate_tool_fail(self, run_id: str, tool: str, error: str) -> ToolResult:
        record = self.manager._ensure_record(run_id)
        run_dir = self.manager._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)
        bus = get_or_create_bus(run_id, run_dir)
        wal.append(WalEventType.TOOL_INTENT, payload={"tool": tool, "simulated": True})
        wal.append(WalEventType.TOOL_STARTED, payload={"tool": tool})
        wal.append(WalEventType.TOOL_FAILED, payload={"tool": tool, "error": error})
        await bus.publish(
            RunEventType.TOOL_FAILED,
            run_state=RunState.TOOL_FAILED,
            message=f"工具失败: {tool}",
            tool=tool,
            payload={"error": error},
        )
        record.error = error
        self.manager._sync_snapshot(record)
        return ToolResult(ok=False, tool=tool, output={}, error=error)

    def _build_ctx(self, run_id: str, record, run_dir: Path) -> dict:
        flags = self.manager._demo_flags.get(run_id, {})
        artifacts = {a.get("name") for a in record.artifacts_meta}

        memory = ResearchMemoryStore(run_dir)
        has_evidence = memory.has_raw_evidence()
        has_synthesis = memory.has_synthesis()
        pdf_path = run_dir / "workspace" / "report.pdf"

        has_report_artifact = "research_report.md" in artifacts
        report_ok = flags.get("report_written") or (
            has_report_artifact and flags.get("quality_passed", False)
        )

        ctx = {
            "has_evidence": has_evidence,
            "has_synthesis": has_synthesis,
            "report_written": report_ok,
            "resume_mode": run_id in self.manager._resume_context,
            "note_written": bool(
                artifacts
                & {"note.md", "recovery_note.md", "after_cancel_demo.md", "pdf_summary.md"}
            ),
            "pdf_extracted": flags.get("pdf_extracted", False),
            "summary_written": "pdf_summary.md" in artifacts,
            "needs_pdf": record.scenario == "summarize_pdf_demo" and not pdf_path.exists(),
            "search_ok": flags.get("search_ok", False),
            "slow_step_done": flags.get("slow_step_done", False),
            "cancelled": self.manager.get_cancel_token(run_id).is_cancelled,
            "quality_passed": flags.get("quality_passed", False),
            "finish_task_called": flags.get("finish_task_called", False),
        }
        if record.scenario == "summarize_pdf_demo" and pdf_path.exists():
            ctx["needs_pdf"] = False
        return ctx

    async def _finalize_outcome(self, run_id: str, outcome: LoopOutcome) -> None:
        run_dir = self.manager._run_dir(run_id)
        wal = WalWriter(run_dir, run_id)

        if outcome == LoopOutcome.SUCCESS:
            wal.append(WalEventType.FINALIZE_INTENT, payload={"outcome": "success"})
            await self.manager.transition(
                run_id,
                RunState.FINALIZING,
                step="finalizing",
                thinking_message="任务收尾",
            )
            wal.append(WalEventType.FINALIZE_COMMITTED, payload={"outcome": "success"})
            await self.manager.transition(
                run_id,
                RunState.SUCCESS,
                step="completed",
                thinking_message="Agent loop 成功完成",
            )
        elif outcome == LoopOutcome.TIMEOUT:
            await self.manager.transition(
                run_id,
                RunState.TIMEOUT,
                step="timeout",
                stop_reason="agent_loop_timeout",
            )
        elif outcome == LoopOutcome.CANCELLED:
            await self.manager.transition(
                run_id,
                RunState.CANCELLED,
                step="cancelled",
                stop_reason="user_cancel",
            )
        elif outcome == LoopOutcome.FAILED:
            record = self.manager.get_record(run_id)
            if record and not is_terminal(record.run_state):
                await self.manager.transition(
                    run_id,
                    RunState.FAILED,
                    step="failed",
                    stop_reason="agent_loop_failed",
                    error=record.error or "agent loop failed",
                )

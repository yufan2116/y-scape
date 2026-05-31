"""Demo scenarios — Phase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class DemoScenario:
    name: str
    goal: str
    description: str
    plan: Callable[[int, str, dict[str, Any]], dict[str, Any]] = field(repr=False)
    task_type: str = "research_report"


def _note_md_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if not ctx.get("note_written"):
        content = f"# 笔记\n\n{goal}\n\n由 Demo Mode 自动生成。\n"
        return {
            "action": "tool",
            "tool": "file_write",
            "params": {
                "name": "note.md",
                "content": content,
                "to_artifact": True,
                "artifact_type": "report",
            },
            "reasoning": f"第 {iteration} 轮：写入 note.md 交付物",
        }
    if not ctx.get("finish_task_called"):
        return {
            "action": "tool",
            "tool": "finish_task",
            "params": {"reason": "note.md delivered"},
            "reasoning": f"第 {iteration} 轮：finish_task 确认交付",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：note.md 已完成"}


def _summarize_pdf_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if ctx.get("needs_pdf"):
        return {
            "action": "needs_input",
            "reasoning": "缺少 workspace/report.pdf，请上传后继续",
            "message": "missing report.pdf",
        }
    if not ctx.get("pdf_extracted"):
        return {
            "action": "tool",
            "tool": "pdf_extract",
            "params": {"path": "report.pdf"},
            "reasoning": f"第 {iteration} 轮：提取 PDF 文本",
        }
    if not ctx.get("summary_written"):
        summary = (
            f"# PDF 摘要\n\n目标：{goal}\n\n"
            "基于 pdf_extract 演示结果生成的摘要报告。\n\n"
            "## 要点\n\n"
            "1. Agent Runtime 需要 WAL 与 Checkpoint。\n"
            "2. 工具调用必须走统一 pipeline。\n"
            "3. 交付物 preview 独立于任务状态。\n"
        )
        return {
            "action": "tool",
            "tool": "file_write",
            "params": {
                "name": "pdf_summary.md",
                "content": summary,
                "to_artifact": True,
                "artifact_type": "report",
            },
            "reasoning": f"第 {iteration} 轮：写入 PDF 摘要",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：PDF 摘要完成"}


def _web_research_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if not ctx.get("has_evidence"):
        return {
            "action": "tool",
            "tool": "web_search",
            "params": {"query": goal},
            "reasoning": f"第 {iteration} 轮：web_search 收集证据（禁止直接写文件）",
        }
    if not ctx.get("report_written"):
        return {
            "action": "synthesize_report",
            "filename": "research_report.md",
            "reasoning": f"第 {iteration} 轮：ResearchMemory → Synthesis → ReportWriter",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：研究报告已完成"}


def _recover_failed_tool_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if not ctx.get("search_ok"):
        return {
            "action": "tool",
            "tool": "web_search",
            "params": {"query": goal},
            "reasoning": f"第 {iteration} 轮：web_search（首次可能失败，需重试）",
        }
    if not ctx.get("note_written"):
        return {
            "action": "tool",
            "tool": "file_write",
            "params": {
                "name": "recovery_note.md",
                "content": f"# 恢复演示\n\n{goal}\n\n工具失败后重试成功。\n",
                "to_artifact": True,
            },
            "reasoning": f"第 {iteration} 轮：工具恢复后写入 note",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：恢复流程完成"}


def _cancel_resume_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if ctx.get("cancelled"):
        return {"action": "cancelled", "reasoning": "任务已被取消"}
    if not ctx.get("slow_step_done"):
        return {
            "action": "slow_step",
            "seconds": 3,
            "reasoning": f"第 {iteration} 轮：可取消的慢步骤（演示 cancel）",
        }
    if not ctx.get("note_written"):
        return {
            "action": "tool",
            "tool": "file_write",
            "params": {
                "name": "after_cancel_demo.md",
                "content": f"# Cancel Demo\n\n{goal}\n",
                "to_artifact": True,
            },
            "reasoning": f"第 {iteration} 轮：取消演示后继续（若未取消）",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：cancel/resume 演示完成"}


def _quality_failure_plan(iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if not ctx.get("has_evidence"):
        return {
            "action": "tool",
            "tool": "web_search",
            "params": {"query": goal},
            "reasoning": f"第 {iteration} 轮：收集证据",
        }
    if not ctx.get("report_written"):
        return {
            "action": "synthesize_report",
            "filename": "research_report.md",
            "reasoning": f"第 {iteration} 轮：综合并写入（首次短稿将被质量门控拒绝）",
        }
    if not ctx.get("quality_passed"):
        return {
            "action": "synthesize_report",
            "filename": "research_report.md",
            "reasoning": f"第 {iteration} 轮：质量修订后重新写入",
        }
    return {"action": "finish", "reasoning": f"第 {iteration} 轮：质量检查通过，任务完成"}


SCENARIOS: dict[str, DemoScenario] = {
    "note_md_demo": DemoScenario(
        name="note_md_demo",
        goal="生成 note.md 演示笔记",
        description="简单 Markdown 笔记交付",
        task_type="simple_note",
        plan=_note_md_plan,
    ),
    "summarize_pdf_demo": DemoScenario(
        name="summarize_pdf_demo",
        goal="总结 workspace/report.pdf",
        description="缺少 PDF 时进入 needs_input",
        task_type="simple_note",
        plan=_summarize_pdf_plan,
    ),
    "web_research_demo": DemoScenario(
        name="web_research_demo",
        goal="研究生成式 AI Agent Runtime 架构",
        description="search → demo synthesis → 800+ 字中文报告",
        task_type="research_report",
        plan=_web_research_plan,
    ),
    "recover_failed_tool_demo": DemoScenario(
        name="recover_failed_tool_demo",
        goal="演示工具失败后重试成功",
        description="首次 web_search 失败，第二次成功",
        task_type="research_report",
        plan=_recover_failed_tool_plan,
    ),
    "cancel_resume_demo": DemoScenario(
        name="cancel_resume_demo",
        goal="演示协作式 cancel",
        description="慢步骤期间可 cancel",
        task_type="simple_note",
        plan=_cancel_resume_plan,
    ),
    "quality_failure_then_revision": DemoScenario(
        name="quality_failure_then_revision",
        goal="质量门控修订演示",
        description="短报告被拒 → 修订后通过质量检查",
        task_type="research_report",
        plan=_quality_failure_plan,
    ),
}


def get_scenario(name: str | None) -> DemoScenario | None:
    if not name:
        return None
    return SCENARIOS.get(name)


def list_scenarios() -> list[dict[str, str]]:
    return [
        {"name": s.name, "goal": s.goal, "description": s.description, "taskType": s.task_type}
        for s in SCENARIOS.values()
    ]

"""Demo LLM — deterministic planner for Demo Mode (no real API)."""

from __future__ import annotations

from typing import Any

from src.demo.scenarios import DemoScenario


class DemoLLM:
    async def plan_next_action(
        self,
        *,
        scenario: DemoScenario | None,
        goal: str,
        iteration: int,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        if scenario:
            return scenario.plan(iteration, goal, ctx)
        return self._default_plan(iteration, goal, ctx)

    def _default_plan(self, iteration: int, goal: str, ctx: dict[str, Any]) -> dict[str, Any]:
        if not ctx.get("has_evidence"):
            return {
                "action": "tool",
                "tool": "web_search",
                "params": {"query": goal},
                "reasoning": f"第 {iteration} 轮：收集研究证据",
            }
        if not ctx.get("report_written"):
            return {
                "action": "synthesize_report",
                "filename": "research_report.md",
                "reasoning": f"第 {iteration} 轮：综合证据并撰写报告",
            }
        return {
            "action": "finish",
            "reasoning": f"第 {iteration} 轮：交付物已就绪，完成任务",
        }

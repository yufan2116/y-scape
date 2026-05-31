"""Planner — Demo Mode or DeepSeek V4 (Phase 4+)."""

from __future__ import annotations

import asyncio
from typing import Any

from src.agent.demo_llm import DemoLLM
from src.agent.llm_planner import LLMPlanner
from src.config import settings
from src.demo.scenarios import DemoScenario, get_scenario
from src.integrations.deepseek_client import DeepSeekError


class Planner:
    def __init__(self, *, demo_mode: bool = True, scenario: str | None = None) -> None:
        self.demo_mode = demo_mode
        self.scenario_name = scenario
        self._demo = DemoLLM()
        self._llm = LLMPlanner()
        self._scenario: DemoScenario | None = get_scenario(scenario) if scenario else None

    async def plan(
        self,
        *,
        goal: str,
        iteration: int,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        timeout = (
            settings.planner_timeout_seconds
            if self.demo_mode
            else settings.llm_timeout_seconds
        )
        if self.demo_mode:
            coro = self._demo.plan_next_action(
                scenario=self._scenario,
                goal=goal,
                iteration=iteration,
                ctx=ctx,
            )
        else:
            if not settings.api_key_configured:
                raise DeepSeekError(
                    "未配置 DeepSeek API Key。请在 backend/.env 设置 DEEPSEEK_API_KEY，"
                    "或创建任务时启用 demoMode"
                )
            coro = self._llm.plan_next_action(goal=goal, iteration=iteration, ctx=ctx)

        return await asyncio.wait_for(coro, timeout=timeout)

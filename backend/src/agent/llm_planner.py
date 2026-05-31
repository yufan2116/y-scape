"""Real LLM planner — DeepSeek V4 structured next-action."""

from __future__ import annotations

import json
from typing import Any

from src.agent.llm_json import extract_json_object
from src.agent.tools import BUILTIN_TOOLS
from src.integrations.deepseek_client import DeepSeekClient, DeepSeekError

_ALLOWED_ACTIONS = frozenset(
    {
        "tool",
        "synthesize_report",
        "finish",
        "needs_input",
    }
)

_TOOL_NAMES = frozenset(BUILTIN_TOOLS)


class LLMPlanner:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    async def plan_next_action(
        self,
        *,
        goal: str,
        iteration: int,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        system = (
            "你是 Y.Scape Agent 的规划器。根据研究目标与当前上下文，输出下一步动作的 JSON。\n"
            "规则：\n"
            "1. 仅输出一个 JSON 对象，无其它文字。\n"
            "2. action 必须是: tool | synthesize_report | finish | needs_input\n"
            "3. action=tool 时必须有 tool（内置工具名）和 params；tool 仅限: "
            + ", ".join(BUILTIN_TOOLS)
            + "\n"
            "4. 尚无证据 (has_evidence=false) 时优先 web_search 收集证据。\n"
            "5. 已有证据且未写报告时，用 synthesize_report（可带 filename，默认 research_report.md）。\n"
            "6. 报告已通过质量门控 (quality_passed=true) 时用 finish。\n"
            "7. 必须包含 reasoning 字段（中文简述）。\n"
            "示例: {\"action\":\"tool\",\"tool\":\"web_search\",\"params\":{\"query\":\"...\"},\"reasoning\":\"...\"}"
        )
        user = json.dumps(
            {
                "goal": goal,
                "iteration": iteration,
                "context": ctx,
            },
            ensure_ascii=False,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            raw = await self._client.chat_completion(messages, json_object=True)
            plan = extract_json_object(raw)
        except (DeepSeekError, ValueError, json.JSONDecodeError) as exc:
            raise DeepSeekError(f"规划失败: {exc}") from exc

        return self._normalize_plan(plan, goal=goal)

    def _normalize_plan(self, plan: dict[str, Any], *, goal: str) -> dict[str, Any]:
        action = str(plan.get("action", "")).strip()
        if action not in _ALLOWED_ACTIONS:
            raise DeepSeekError(f"无效 action: {action!r}")

        reasoning = str(plan.get("reasoning", "")).strip() or f"第 {action} 步"
        out: dict[str, Any] = {"action": action, "reasoning": reasoning}

        if action == "tool":
            tool = str(plan.get("tool", "")).strip()
            if tool not in _TOOL_NAMES:
                raise DeepSeekError(f"无效 tool: {tool!r}")
            params = plan.get("params")
            if not isinstance(params, dict):
                params = {}
            if tool == "web_search" and "query" not in params:
                params["query"] = goal
            out["tool"] = tool
            out["params"] = params

        if action == "synthesize_report":
            out["filename"] = str(plan.get("filename", "research_report.md")).strip() or "research_report.md"

        if action == "needs_input":
            out["message"] = str(plan.get("message", "需要更多信息"))

        return out

"""DeepSeek LLM planner/synthesis tests (mocked HTTP)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.agent.llm_planner import LLMPlanner
from src.agent.llm_synthesis import LLMSynthesis
from src.agent.research_memory import ResearchMemoryStore
from src.integrations.deepseek_client import DeepSeekClient


@pytest.mark.asyncio
async def test_llm_planner_parses_json_plan(isolated_runs_dir):
    plan_json = json.dumps(
        {
            "action": "tool",
            "tool": "web_search",
            "params": {"query": "agent runtime"},
            "reasoning": "收集证据",
        },
        ensure_ascii=False,
    )
    client = DeepSeekClient()
    client.chat_completion = AsyncMock(return_value=plan_json)  # type: ignore[method-assign]

    planner = LLMPlanner(client=client)
    plan = await planner.plan_next_action(
        goal="研究 Agent Runtime",
        iteration=1,
        ctx={"has_evidence": False, "report_written": False},
    )
    assert plan["action"] == "tool"
    assert plan["tool"] == "web_search"
    assert plan["params"]["query"] == "agent runtime"


@pytest.mark.asyncio
async def test_llm_synthesis_builds_result(isolated_runs_dir):
    run_dir = isolated_runs_dir / "run_llm_syn"
    run_dir.mkdir()
    (run_dir / "research_memory").mkdir()
    memory = ResearchMemoryStore(run_dir)
    memory.append_raw_evidence(
        {
            "source_id": "src_001",
            "title": "Agent Runtime",
            "url": "https://example.com/a",
            "content": "长时运行 Agent 需要 WAL 与 Checkpoint，支持可恢复执行。",
        }
    )

    synthesis_json = json.dumps(
        {
            "executive_summary": "针对 Agent Runtime 的研究摘要，涵盖 WAL 与恢复能力。",
            "key_trends": ["可恢复执行", "结构化事件流"],
            "important_papers": ["WAL for Agents"],
            "industry_news": ["Runtime 产品化"],
            "risks": ["质量门控复杂度"],
            "future_directions": ["E2E 测试"],
            "contradictions": [],
        },
        ensure_ascii=False,
    )
    client = DeepSeekClient()
    client.chat_completion = AsyncMock(return_value=synthesis_json)  # type: ignore[method-assign]

    engine = LLMSynthesis(client=client)
    result = await engine.synthesize(memory, goal="研究 Agent Runtime")

    assert "WAL" in result.executive_summary
    assert len(result.key_trends) >= 2
    assert len(result.sources) == 1
    assert memory.has_synthesis()

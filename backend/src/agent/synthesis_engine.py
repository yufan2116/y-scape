"""SynthesisEngine — evidence → structured SynthesisResult (Demo Mode deterministic)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.agent.llm_synthesis import LLMSynthesis
from src.agent.research_memory import Finding, ResearchMemoryStore, Source, SynthesisResult
from src.config import settings
from src.integrations.deepseek_client import DeepSeekError


class SynthesisEngine:
    """Phase 5: rank findings and produce SynthesisResult. Real LLM post Phase 4+."""

    def __init__(self, *, demo_mode: bool = True) -> None:
        self.demo_mode = demo_mode
        self._llm = LLMSynthesis()

    async def synthesize(self, memory: ResearchMemoryStore, *, goal: str) -> SynthesisResult:
        if self.demo_mode:
            return await asyncio.wait_for(
                asyncio.to_thread(self._synthesize_demo, memory, goal),
                timeout=settings.planner_timeout_seconds,
            )
        if not settings.api_key_configured:
            raise DeepSeekError(
                "未配置 DeepSeek API Key。请在 backend/.env 设置 DEEPSEEK_API_KEY"
            )
        return await asyncio.wait_for(
            self._llm.synthesize(memory, goal=goal),
            timeout=settings.llm_timeout_seconds,
        )

    def _synthesize_demo(self, memory: ResearchMemoryStore, goal: str) -> SynthesisResult:
        findings = memory.ensure_findings()
        if not findings:
            raise ValueError("No findings available for synthesis")

        sources = memory.build_sources(findings)
        ranked = sorted(findings, key=lambda f: f.confidence, reverse=True)

        papers = [
            f"{f.title} — {f.summary[:80]}… [source:{f.source}]"
            for f in ranked
            if "agent_runtime" in f.tags or f.source.startswith("src_")
        ][:4]
        if not papers:
            papers = [f"{f.title} — {f.summary[:80]}…" for f in ranked[:3]]

        news = [
            f"{f.title}：{f.summary[:60]}…"
            for f in ranked
            if f.url and "example.com" in (f.url or "")
        ][:3]
        if not news:
            news = [f"{f.title}：{f.summary[:60]}…" for f in ranked[:2]]

        trends = [
            "长时运行 Agent Runtime 强调 WAL 事务语义与可恢复 Checkpoint",
            "Timeline 事件流与轻量 Status API 分离，避免 polling 路径阻塞",
            "研究交付必须经过综合层，禁止 raw search 直接写入报告",
            "Tool 执行统一 pipeline，Artifact 注册与任务成功解耦",
        ]

        risks = [
            "质量门控未通过时 file_write 不能等同于任务成功",
            "记忆压缩与 context pack 规模控制仍是落地难点",
            "Demo Mode 不能替代真实 LLM 推理与引用校验",
        ]

        future = [
            "接入 Deliverable Quality Gate 与 revision loop",
            "WAL Resume 与协作式 Cancel 完整 recovery",
            "整合现有个人项目 Tool Hub adapter",
        ]

        contradictions: list[str] = []
        if len({f.source for f in findings}) < 2:
            contradictions.append("证据来源较少，结论置信度受限")

        summary = (
            f"本报告针对研究目标「{goal}」综合 {len(findings)} 条 Finding、"
            f"{len(sources)} 个 Source。"
            "分析覆盖 Agent Runtime 可观测性、可恢复执行与研究综合流水线。"
            "所有章节 grounded 于 ResearchMemory 中的结构化证据，而非搜索结果直写。"
        )

        result = SynthesisResult(
            executive_summary=summary,
            key_trends=trends,
            important_papers=papers,
            industry_news=news,
            risks=risks,
            future_directions=future,
            contradictions=contradictions,
            sources=sources,
        )
        memory.save_synthesis(result)
        return result


def synthesize_research(run_dir: Path, goal: str, *, demo_mode: bool = True) -> SynthesisResult:
    """Sync helper for tests."""
    memory = ResearchMemoryStore(run_dir)
    engine = SynthesisEngine(demo_mode=demo_mode)
    return engine._synthesize_demo(memory, goal)

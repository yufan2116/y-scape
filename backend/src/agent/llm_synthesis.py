"""Real LLM research synthesis — DeepSeek V4 → SynthesisResult."""

from __future__ import annotations

import json
from typing import Any

from src.agent.llm_json import extract_json_object
from src.agent.research_memory import Finding, ResearchMemoryStore, Source, SynthesisResult
from src.integrations.deepseek_client import DeepSeekClient, DeepSeekError


class LLMSynthesis:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self._client = client or DeepSeekClient()

    async def synthesize(self, memory: ResearchMemoryStore, *, goal: str) -> SynthesisResult:
        findings = memory.ensure_findings()
        if not findings:
            raise ValueError("No findings available for synthesis")

        sources = memory.build_sources(findings)
        evidence_blob = self._format_findings(findings)

        system = (
            "你是研究综合引擎。仅根据提供的 findings 生成结构化 JSON，禁止编造未出现的来源。\n"
            "输出字段（均为 JSON）：\n"
            "- executive_summary: string\n"
            "- key_trends: string[]\n"
            "- important_papers: string[]\n"
            "- industry_news: string[]\n"
            "- risks: string[]\n"
            "- future_directions: string[]\n"
            "- contradictions: string[]\n"
            "不要包含 sources 字段（由系统填充）。仅输出 JSON 对象。"
        )
        user = json.dumps(
            {"goal": goal, "findings": evidence_blob},
            ensure_ascii=False,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            raw = await self._client.chat_completion(messages, json_object=True)
            data = extract_json_object(raw)
        except (DeepSeekError, ValueError, json.JSONDecodeError) as exc:
            raise DeepSeekError(f"综合失败: {exc}") from exc

        result = self._to_synthesis_result(data, sources=sources)
        memory.save_synthesis(result)
        return result

    @staticmethod
    def _format_findings(findings: list[Finding]) -> list[dict[str, Any]]:
        return [
            {
                "title": f.title,
                "summary": f.summary,
                "source": f.source,
                "url": f.url,
                "tags": f.tags,
                "confidence": f.confidence,
            }
            for f in findings
        ]

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _to_synthesis_result(self, data: dict[str, Any], *, sources: list[Source]) -> SynthesisResult:
        summary = str(data.get("executive_summary", "")).strip()
        if not summary:
            raise DeepSeekError("综合结果缺少 executive_summary")

        return SynthesisResult(
            executive_summary=summary,
            key_trends=self._string_list(data.get("key_trends")),
            important_papers=self._string_list(data.get("important_papers")),
            industry_news=self._string_list(data.get("industry_news")),
            risks=self._string_list(data.get("risks")),
            future_directions=self._string_list(data.get("future_directions")),
            contradictions=self._string_list(data.get("contradictions")),
            sources=sources,
        )

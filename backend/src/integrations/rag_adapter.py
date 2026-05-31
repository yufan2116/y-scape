"""Local RAG adapter stub — P0."""

from __future__ import annotations

from typing import Any

from src.integrations.base import AdapterStatus, ToolAdapter


class LocalRagQueryAdapter(ToolAdapter):
    name = "local_rag_query"
    description = "本地 RAG + Ollama 问答"
    source_project = "RAG"
    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "doc_dir": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["question"],
    }
    output_schema = {"type": "object"}

    async def validate_input(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if not params.get("question"):
            return False, "question required"
        return True, None

    async def run(self, params: dict[str, Any], *, dry_run: bool = True, timeout: float = 30.0) -> dict[str, Any]:
        return {"ok": False, "error": "stub — 未配置 RAG 项目路径"}

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

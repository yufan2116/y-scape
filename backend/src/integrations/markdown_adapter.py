"""Markdown convert adapter stub — P0."""

from __future__ import annotations

from typing import Any

from src.integrations.base import AdapterStatus, ToolAdapter


class MarkdownConvertAdapter(ToolAdapter):
    name = "markdown_convert"
    description = "Pandoc / PDF 转 Markdown"
    source_project = "MARKDOWN"
    input_schema = {
        "type": "object",
        "properties": {"input_path": {"type": "string"}},
        "required": ["input_path"],
    }
    output_schema = {"type": "object"}

    async def validate_input(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if not params.get("input_path"):
            return False, "input_path required"
        return True, None

    async def run(self, params: dict[str, Any], *, dry_run: bool = True, timeout: float = 30.0) -> dict[str, Any]:
        return {"ok": False, "error": "stub — 未配置 MARKDOWN 项目路径"}

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

"""Markdown convert adapter."""

from __future__ import annotations

from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig


class MarkdownConvertAdapter(BaseToolAdapter):
    tool_id = "markdown_convert"
    display_name = "MARKDOWN"
    description = "Pandoc / PDF 转 Markdown"
    source_project = "MARKDOWN"
    category = "Research"
    input_summary = "input_path · output_path (optional)"
    input_schema = {
        "type": "object",
        "properties": {
            "input_path": {"type": "string"},
            "output_path": {"type": "string"},
        },
        "required": ["input_path"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if not input_data.get("input_path"):
            return {"ok": False, "error": "input_path is required", "status": AdapterStatus.ERROR}

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": dry_run}

        if dry_run:
            return await self._stub_run(
                input_data,
                dry_run=True,
                message=f"Dry run — would convert {input_data['input_path']}",
            )

        return await self._run_subprocess(dry_run=False, input_data=input_data)

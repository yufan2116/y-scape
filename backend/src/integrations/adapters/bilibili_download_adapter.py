"""Bilibili download tool adapter."""

from __future__ import annotations

from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig


class BilibiliDownloadAdapter(BaseToolAdapter):
    tool_id = "bilibili_download"
    display_name = "Download-tool"
    description = "B 站视频下载工具"
    source_project = "Download-tool"
    category = "Media"
    input_summary = "url · output_dir (required)"
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Bilibili video URL"},
            "output_dir": {"type": "string", "description": "Download output directory"},
        },
        "required": ["url", "output_dir"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if not input_data.get("url"):
            return {"ok": False, "error": "url is required", "status": AdapterStatus.ERROR}
        output_dir = input_data.get("output_dir")
        if not output_dir:
            return {"ok": False, "error": "output_dir is required", "status": AdapterStatus.ERROR}

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": dry_run}

        if dry_run:
            return await self._stub_run(
                input_data,
                dry_run=True,
                message=f"Dry run — would download to {output_dir}",
            )

        result = await self._run_subprocess(dry_run=False, input_data=input_data)
        result["outputDir"] = output_dir
        return result

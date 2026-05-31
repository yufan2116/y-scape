"""Folder clean adapter — dry_run defaults to true."""

from __future__ import annotations

from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig


class FolderCleanAdapter(BaseToolAdapter):
    tool_id = "folder_clean"
    display_name = "Folder Clean"
    description = "文件夹清理 Web API"
    source_project = "folder clean"
    category = "Automation"
    input_summary = "target_dir · dry_run (default true)"
    input_schema = {
        "type": "object",
        "properties": {
            "target_dir": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True},
            "confirm_delete": {"type": "boolean", "default": False},
        },
        "required": ["target_dir"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if not input_data.get("target_dir"):
            return {"ok": False, "error": "target_dir is required", "status": AdapterStatus.ERROR}

        effective_dry = input_data.get("dry_run", dry_run if dry_run else True)
        if effective_dry is False and not input_data.get("confirm_delete"):
            return {
                "ok": False,
                "error": "Deleting files requires confirm_delete=true",
                "status": AdapterStatus.ERROR,
                "dryRun": True,
            }

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": effective_dry}

        run_dry = bool(effective_dry) or dry_run
        if run_dry:
            return await self._stub_run(
                {**input_data, "dry_run": True},
                dry_run=True,
                message="Dry run — no files will be deleted",
            )

        return await self._run_subprocess(dry_run=False, input_data={**input_data, "dry_run": False})

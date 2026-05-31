"""Folder clean adapter stub — P0, dry_run default."""

from __future__ import annotations

from typing import Any

from src.integrations.base import AdapterStatus, ToolAdapter


class FolderCleanAdapter(ToolAdapter):
    name = "folder_clean"
    description = "文件夹清理（dry_run 默认开启）"
    source_project = "folder clean"
    input_schema = {
        "type": "object",
        "properties": {
            "target_dir": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True},
        },
        "required": ["target_dir"],
    }
    output_schema = {"type": "object"}

    async def validate_input(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        if not params.get("target_dir"):
            return False, "target_dir required"
        return True, None

    async def run(self, params: dict[str, Any], *, dry_run: bool = True, timeout: float = 30.0) -> dict[str, Any]:
        effective_dry = params.get("dry_run", dry_run)
        return {
            "ok": True,
            "dry_run": effective_dry,
            "message": "stub — 未配置 folder clean 项目路径",
            "files": [],
        }

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

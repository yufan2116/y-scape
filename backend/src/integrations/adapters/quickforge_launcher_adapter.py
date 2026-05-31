"""QuickForge launcher adapter — allowlisted scripts only."""

from __future__ import annotations

from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig

ALLOWLISTED_SCRIPTS = frozenset(
    {
        "launch.py",
        "run_script.py",
        "quickforge_launch.py",
        "main.py",
    }
)


class QuickForgeLauncherAdapter(BaseToolAdapter):
    tool_id = "quickforge_launcher"
    display_name = "QuickForge Launcher"
    description = "Tauri 脚本启动器"
    source_project = "QuickForge Launcher"
    category = "Automation"
    input_summary = "script_name (allowlist) · args"
    input_schema = {
        "type": "object",
        "properties": {
            "script_name": {"type": "string"},
            "args": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["script_name"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        script_name = input_data.get("script_name")
        if not script_name:
            return {"ok": False, "error": "script_name is required", "status": AdapterStatus.ERROR}

        base_name = str(script_name).replace("\\", "/").split("/")[-1]
        if base_name not in ALLOWLISTED_SCRIPTS:
            return {
                "ok": False,
                "error": f"script_name not in allowlist: {sorted(ALLOWLISTED_SCRIPTS)}",
                "status": AdapterStatus.ERROR,
            }

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": dry_run}

        if dry_run:
            return await self._stub_run(
                input_data,
                dry_run=True,
                message=f"Dry run — would launch allowlisted script {base_name}",
            )

        extra = [str(script_name)]
        args = input_data.get("args")
        if isinstance(args, list):
            extra.extend(str(a) for a in args)
        return await self._run_subprocess(extra_args=extra, dry_run=False, input_data=input_data)

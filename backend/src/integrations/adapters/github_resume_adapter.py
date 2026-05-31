"""GitHub resume generator adapter."""

from __future__ import annotations

from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig


class GithubResumeAdapter(BaseToolAdapter):
    tool_id = "github_resume_generator"
    display_name = "GitHub Resume Generator"
    description = "Generate STAR resume bullets from GitHub repositories."
    source_project = "GitHub Resume Generator"
    category = "Portfolio"
    input_summary = "repo_url · github_token (optional)"
    input_schema = {
        "type": "object",
        "properties": {
            "repo_url": {"type": "string"},
            "github_token": {"type": "string"},
        },
        "required": ["repo_url"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if not input_data.get("repo_url"):
            return {"ok": False, "error": "repo_url is required", "status": AdapterStatus.ERROR}

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": dry_run}

        if dry_run:
            return await self._stub_run(
                input_data,
                dry_run=True,
                message=f"Dry run — would analyze {input_data['repo_url']}",
            )

        return await self._run_subprocess(dry_run=False, input_data=input_data)

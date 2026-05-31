"""GitHub resume adapter stub — P1."""

from src.integrations.base import AdapterStatus, ToolAdapter


class GithubResumeAdapter(ToolAdapter):
    name = "github_resume_generator"
    description = "GitHub 仓库 → STAR 简历描述"
    source_project = "GitHub Resume Generator"
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}

    async def validate_input(self, params):  # type: ignore[no-untyped-def]
        return False, "P1 — not implemented"

    async def run(self, params, *, dry_run=True, timeout=30.0):  # type: ignore[no-untyped-def]
        return {"ok": False, "error": "P1 — not implemented"}

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

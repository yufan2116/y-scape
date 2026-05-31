"""QuickForge adapter stub — P3."""

from src.integrations.base import AdapterStatus, ToolAdapter


class QuickForgeAdapter(ToolAdapter):
    name = "quickforge_launcher"
    description = "Tauri 脚本启动器"
    source_project = "QuickForge Launcher"
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}

    async def validate_input(self, params):  # type: ignore[no-untyped-def]
        return False, "P3 — not implemented"

    async def run(self, params, *, dry_run=True, timeout=30.0):  # type: ignore[no-untyped-def]
        return {"ok": False, "error": "P3 — not implemented"}

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

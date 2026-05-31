"""Download tool adapter stub — P2."""

from src.integrations.base import AdapterStatus, ToolAdapter


class DownloadToolAdapter(ToolAdapter):
    name = "video_download"
    description = "B站视频下载"
    source_project = "Download-tool"
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}

    async def validate_input(self, params):  # type: ignore[no-untyped-def]
        return False, "P2 — not implemented"

    async def run(self, params, *, dry_run=True, timeout=30.0):  # type: ignore[no-untyped-def]
        return {"ok": False, "error": "P2 — not implemented"}

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.NOT_CONFIGURED

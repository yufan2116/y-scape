"""Local RAG query adapter — doc_dir must be user-specified."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig


class LocalRagAdapter(BaseToolAdapter):
    tool_id = "local_rag_query"
    display_name = "Local RAG"
    description = "本地 RAG + Ollama"
    source_project = "RAG"
    category = "Research"
    input_summary = "question · doc_dir (required) · top_k"
    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "doc_dir": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["question", "doc_dir"],
    }

    def __init__(self, config: ToolIntegrationConfig) -> None:
        super().__init__(config)

    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        if not input_data.get("question"):
            return {"ok": False, "error": "question is required", "status": AdapterStatus.ERROR}

        doc_dir = input_data.get("doc_dir")
        if not doc_dir:
            return {"ok": False, "error": "doc_dir is required — RAG only reads user-specified directories", "status": AdapterStatus.ERROR}

        doc_path = Path(str(doc_dir))
        if not doc_path.exists() or not doc_path.is_dir():
            return {"ok": False, "error": f"doc_dir does not exist: {doc_dir}", "status": AdapterStatus.ERROR}

        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not configured", "status": status, "dryRun": dry_run}

        if dry_run:
            return await self._stub_run(
                input_data,
                dry_run=True,
                message=f"Dry run — would query docs in {doc_dir}",
            )

        return await self._run_subprocess(dry_run=False, input_data=input_data)

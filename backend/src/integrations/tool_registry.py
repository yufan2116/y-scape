"""Integration tool registry — wires config + adapters."""

from __future__ import annotations

from typing import Any, Type

from src.integrations.adapters.bilibili_download_adapter import BilibiliDownloadAdapter
from src.integrations.adapters.folder_clean_adapter import FolderCleanAdapter
from src.integrations.adapters.github_resume_adapter import GithubResumeAdapter
from src.integrations.adapters.local_rag_adapter import LocalRagAdapter
from src.integrations.adapters.markdown_convert_adapter import MarkdownConvertAdapter
from src.integrations.adapters.quickforge_launcher_adapter import QuickForgeLauncherAdapter
from src.integrations.base_adapter import AdapterStatus, BaseToolAdapter
from src.integrations.config import ToolIntegrationConfig, load_run_history, load_tool_configs, update_tool_config

ADAPTER_CLASSES: dict[str, Type[BaseToolAdapter]] = {
    "bilibili_download": BilibiliDownloadAdapter,
    "folder_clean": FolderCleanAdapter,
    "github_resume_generator": GithubResumeAdapter,
    "markdown_convert": MarkdownConvertAdapter,
    "quickforge_launcher": QuickForgeLauncherAdapter,
    "local_rag_query": LocalRagAdapter,
}


class ToolRegistry:
    def __init__(self) -> None:
        self._reload()

    def _reload(self) -> None:
        self._configs = load_tool_configs()
        self._adapters: dict[str, BaseToolAdapter] = {}
        for tool_id, cls in ADAPTER_CLASSES.items():
            cfg = self._configs.get(tool_id)
            if cfg is None:
                continue
            self._adapters[tool_id] = cls(cfg)

    def reload(self) -> None:
        self._reload()

    def get(self, tool_id: str) -> BaseToolAdapter | None:
        return self._adapters.get(tool_id)

    def list_tool_ids(self) -> list[str]:
        return list(ADAPTER_CLASSES.keys())

    def get_config(self, tool_id: str) -> ToolIntegrationConfig | None:
        return self._configs.get(tool_id)

    def update_config(self, config: ToolIntegrationConfig) -> ToolIntegrationConfig:
        saved = update_tool_config(config)
        self._configs[saved.tool_id] = saved
        cls = ADAPTER_CLASSES.get(saved.tool_id)
        if cls:
            self._adapters[saved.tool_id] = cls(saved)
        return saved

    def list_configs(self) -> list[ToolIntegrationConfig]:
        return [self._configs[tid] for tid in sorted(self._configs.keys()) if tid in ADAPTER_CLASSES]

    async def _tool_payload(self, tool_id: str, adapter: BaseToolAdapter) -> dict[str, Any]:
        status, message = await adapter.health_check()
        history = load_run_history()
        meta = adapter.metadata()
        cfg = self._configs.get(tool_id)
        return {
            **meta,
            "status": status,
            "statusMessage": message,
            "lastRunAt": history.get(tool_id),
            "projectPath": cfg.project_path if cfg else "",
            "pythonExecutable": cfg.python_executable if cfg else "",
            "entryScript": cfg.entry_script if cfg else "",
            "workingDirectory": cfg.working_directory if cfg else "",
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for tool_id in self.list_tool_ids():
            adapter = self._adapters.get(tool_id)
            if adapter is None:
                continue
            items.append(await self._tool_payload(tool_id, adapter))
        return items

    async def get_tool(self, tool_id: str) -> dict[str, Any] | None:
        adapter = self._adapters.get(tool_id)
        if adapter is None:
            return None
        return await self._tool_payload(tool_id, adapter)

    async def health_check(self, tool_id: str) -> dict[str, Any]:
        adapter = self._adapters.get(tool_id)
        if adapter is None:
            return {"ok": False, "error": f"Unknown tool: {tool_id}"}
        try:
            status, message = await adapter.health_check()
            valid, valid_err = adapter.validate_config()
            return {
                "toolId": tool_id,
                "status": status,
                "message": message,
                "configValid": valid,
                "configError": valid_err,
            }
        except Exception as exc:
            return {
                "toolId": tool_id,
                "status": AdapterStatus.ERROR,
                "message": str(exc),
                "configValid": False,
                "configError": str(exc),
            }

    async def run_tool(
        self,
        tool_id: str,
        input_data: dict[str, Any],
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        adapter = self._adapters.get(tool_id)
        if adapter is None:
            return {"ok": False, "error": f"Unknown tool: {tool_id}", "status": AdapterStatus.ERROR}
        try:
            return await adapter.run(input_data, dry_run=dry_run)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "status": AdapterStatus.ERROR, "dryRun": dry_run}

    def list_metadata(self) -> list[dict[str, Any]]:
        """Backward-compatible metadata for phase-1 tests."""
        items: list[dict[str, Any]] = []
        for tool_id, adapter in self._adapters.items():
            meta = adapter.metadata()
            items.append(
                {
                    "name": tool_id,
                    "description": meta["description"],
                    "sourceProject": meta["sourceProject"],
                    "status": "pending_health_check",
                    "inputSchema": meta["inputSchema"],
                }
            )
        return items

    async def health_check_all(self) -> list[dict[str, Any]]:
        """Backward-compatible health check list for phase-1 tests."""
        results: list[dict[str, Any]] = []
        for tool_id, adapter in self._adapters.items():
            try:
                status, message = await adapter.health_check()
            except Exception as exc:
                results.append(
                    {
                        "name": tool_id,
                        "status": AdapterStatus.ERROR,
                        "sourceProject": adapter.source_project,
                        "error": str(exc),
                    }
                )
                continue
            entry: dict[str, Any] = {
                "name": tool_id,
                "status": status,
                "sourceProject": adapter.source_project,
            }
            if message:
                entry["message"] = message
            results.append(entry)
        return results


default_tool_registry = ToolRegistry()

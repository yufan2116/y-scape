"""Tool integration configuration — persisted to backend/config/tool_integrations.json."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(os.environ.get("YSCAPE_TOOL_CONFIG_DIR", "")).resolve() if os.environ.get("YSCAPE_TOOL_CONFIG_DIR") else Path(__file__).resolve().parents[2] / "config"
_CONFIG_PATH = _CONFIG_DIR / "tool_integrations.json"
_RUN_HISTORY_PATH = _CONFIG_DIR / "tool_run_history.json"


@dataclass
class ToolIntegrationConfig:
    tool_id: str
    display_name: str
    description: str
    source_project: str = ""
    category: str = ""
    project_path: str = ""
    python_executable: str = ""
    entry_script: str = ""
    working_directory: str = ""
    enabled: bool = False
    timeout_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolIntegrationConfig:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


DEFAULT_TOOL_CONFIGS: list[ToolIntegrationConfig] = [
    ToolIntegrationConfig(
        tool_id="bilibili_download",
        display_name="Download-tool",
        description="B 站视频下载工具",
        source_project="Download-tool",
        category="Media",
    ),
    ToolIntegrationConfig(
        tool_id="folder_clean",
        display_name="Folder Clean",
        description="文件夹清理 Web API",
        source_project="folder clean",
        category="Automation",
    ),
    ToolIntegrationConfig(
        tool_id="github_resume_generator",
        display_name="GitHub Resume Generator",
        description="Generate STAR resume bullets from GitHub repositories.",
        source_project="GitHub Resume Generator",
        category="Portfolio",
    ),
    ToolIntegrationConfig(
        tool_id="markdown_convert",
        display_name="MARKDOWN",
        description="Pandoc / PDF 转 Markdown",
        source_project="MARKDOWN",
        category="Research",
    ),
    ToolIntegrationConfig(
        tool_id="quickforge_launcher",
        display_name="QuickForge Launcher",
        description="Tauri 脚本启动器",
        source_project="QuickForge Launcher",
        category="Automation",
    ),
    ToolIntegrationConfig(
        tool_id="local_rag_query",
        display_name="Local RAG",
        description="本地 RAG + Ollama",
        source_project="RAG",
        category="Research",
    ),
]


def _ensure_config_dir() -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_tool_configs() -> dict[str, ToolIntegrationConfig]:
    _ensure_config_dir()
    if not _CONFIG_PATH.exists():
        save_tool_configs({c.tool_id: c for c in DEFAULT_TOOL_CONFIGS})
        return {c.tool_id: ToolIntegrationConfig(**asdict(c)) for c in DEFAULT_TOOL_CONFIGS}

    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    tools_raw = raw.get("tools", raw if isinstance(raw, list) else [])
    if isinstance(tools_raw, dict):
        items = tools_raw.values()
    else:
        items = tools_raw

    configs: dict[str, ToolIntegrationConfig] = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("tool_id"):
            continue
        configs[item["tool_id"]] = ToolIntegrationConfig.from_dict(item)

    for default in DEFAULT_TOOL_CONFIGS:
        if default.tool_id not in configs:
            configs[default.tool_id] = ToolIntegrationConfig(**asdict(default))

    return configs


def save_tool_configs(configs: dict[str, ToolIntegrationConfig]) -> None:
    _ensure_config_dir()
    ordered = [configs[tid].to_dict() for tid in sorted(configs.keys())]
    payload = {"tools": ordered}
    _CONFIG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_tool_config(config: ToolIntegrationConfig) -> ToolIntegrationConfig:
    configs = load_tool_configs()
    existing = configs.get(config.tool_id)
    if existing:
        merged = ToolIntegrationConfig.from_dict({**existing.to_dict(), **config.to_dict()})
    else:
        merged = config
    configs[merged.tool_id] = merged
    save_tool_configs(configs)
    return merged


def load_run_history() -> dict[str, str | None]:
    _ensure_config_dir()
    if not _RUN_HISTORY_PATH.exists():
        return {}
    try:
        data = json.loads(_RUN_HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, str) or v is None}
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def record_run(tool_id: str, timestamp: str) -> None:
    _ensure_config_dir()
    history = load_run_history()
    history[tool_id] = timestamp
    _RUN_HISTORY_PATH.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

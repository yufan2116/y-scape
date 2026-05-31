"""System-wide settings persisted to backend/config/system_settings.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.config import settings

_CONFIG_DIR = (
    Path(os.environ.get("YSCAPE_TOOL_CONFIG_DIR", "")).resolve()
    if os.environ.get("YSCAPE_TOOL_CONFIG_DIR")
    else Path(__file__).resolve().parents[2] / "config"
)
_SETTINGS_PATH = _CONFIG_DIR / "system_settings.json"


def _defaults() -> dict[str, Any]:
    return {
        "model": {
            "provider": settings.model_provider,
            "modelName": settings.model_name,
            "apiKeyConfigured": settings.api_key_configured,
            "demoMode": settings.demo_mode,
        },
        "storage": {
            "workspaceRoot": str(settings.workspace_root),
            "artifactRoot": str(settings.artifact_root),
            "maxArtifactSizeMb": settings.max_artifact_size_mb,
        },
        "tool": {
            "enabledTools": [
                "markdown_convert",
                "folder_clean",
                "github_resume_generator",
                "local_rag_query",
                "bilibili_download",
                "quickforge_launcher",
            ],
            "defaultOutputDirectory": str(settings.default_output_dir),
            "dryRunDefault": settings.dry_run_default,
        },
        "runtime": {
            "maxIterations": settings.max_iterations,
            "plannerTimeoutSeconds": settings.planner_timeout_seconds,
            "toolTimeoutSeconds": settings.tool_timeout_seconds,
            "statusPollingIntervalMs": settings.status_polling_interval_ms,
        },
        "advanced": {
            "externalIntegrationsEnabled": False,
        },
    }


def load_system_settings() -> dict[str, Any]:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not _SETTINGS_PATH.exists():
        data = _defaults()
        save_system_settings(data)
        return data
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        base = _defaults()
        for key in base:
            if key not in data:
                data[key] = base[key]
            elif isinstance(base[key], dict):
                merged = {**base[key], **data[key]}
                data[key] = merged
        return data
    except (json.JSONDecodeError, OSError):
        return _defaults()


def save_system_settings(data: dict[str, Any]) -> dict[str, Any]:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = load_system_settings() if _SETTINGS_PATH.exists() else _defaults()
    for section, values in data.items():
        if isinstance(values, dict) and isinstance(current.get(section), dict):
            current[section] = {**current[section], **values}
        else:
            current[section] = values
    _SETTINGS_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current

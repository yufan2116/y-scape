"""Settings API — system configuration (primary) + legacy integration paths (advanced)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.integrations.config import ToolIntegrationConfig
from src.integrations.tool_registry import default_tool_registry
from src.system_settings.config import load_system_settings, save_system_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SystemSettingsUpdate(BaseModel):
    model: dict[str, Any] | None = None
    storage: dict[str, Any] | None = None
    tool: dict[str, Any] | None = None
    runtime: dict[str, Any] | None = None
    advanced: dict[str, Any] | None = None


class ToolPathConfigPayload(BaseModel):
    tool_id: str
    display_name: str | None = None
    description: str | None = None
    project_path: str | None = None
    python_executable: str | None = None
    entry_script: str | None = None
    working_directory: str | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)


class ToolPathsUpdateRequest(BaseModel):
    tools: list[ToolPathConfigPayload] | None = None
    tool: ToolPathConfigPayload | None = None


@router.get("")
async def get_system_settings():
    return load_system_settings()


@router.post("")
async def update_system_settings(body: SystemSettingsUpdate):
    patch = body.model_dump(exclude_none=True)
    return save_system_settings(patch)


@router.get("/tool-paths")
async def get_tool_paths():
    """Legacy external integration paths — advanced use only."""
    configs = default_tool_registry.list_configs()
    enriched = []
    for cfg in configs:
        adapter = default_tool_registry.get(cfg.tool_id)
        status = "not_configured"
        message = None
        if adapter:
            status, message = await adapter.health_check()
        enriched.append({**cfg.to_dict(), "status": status, "statusMessage": message})
    return {"tools": enriched}


@router.post("/tool-paths")
async def save_tool_paths(body: ToolPathsUpdateRequest):
    payloads = body.tools or ([body.tool] if body.tool else [])
    if not payloads:
        raise HTTPException(status_code=400, detail="Provide tool or tools in request body")

    saved: list[dict] = []
    for payload in payloads:
        existing = default_tool_registry.get_config(payload.tool_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {payload.tool_id}")

        merged = ToolIntegrationConfig.from_dict(
            {**existing.to_dict(), **payload.model_dump(exclude_none=True)}
        )
        updated = default_tool_registry.update_config(merged)
        adapter = default_tool_registry.get(updated.tool_id)
        status = "not_configured"
        message = None
        if adapter:
            status, message = await adapter.health_check()
        saved.append({**updated.to_dict(), "status": status, "statusMessage": message})

    return {"tools": saved}

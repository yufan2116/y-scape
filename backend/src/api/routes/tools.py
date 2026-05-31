"""Tool Hub API — native tools primary; legacy integration adapters secondary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.integrations.tool_registry import default_tool_registry
from src.native_tools.registry import list_native_tools

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolRunRequest(BaseModel):
    input: dict = Field(default_factory=dict)
    dry_run: bool = True


@router.get("")
async def list_tools():
    """Primary: native built-in tool modules."""
    return list_native_tools()


@router.get("/integrations")
async def list_integration_adapters():
    """Legacy external adapter health checks — not used by Tool Hub UI."""
    return await default_tool_registry.health_check_all()


@router.get("/integrations/{tool_id}")
async def get_integration_adapter(tool_id: str):
    tool = await default_tool_registry.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {tool_id}")
    return tool


@router.post("/integrations/{tool_id}/health-check")
async def health_check_integration(tool_id: str):
    if default_tool_registry.get(tool_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {tool_id}")
    return await default_tool_registry.health_check(tool_id)


@router.post("/integrations/{tool_id}/run")
async def run_integration(tool_id: str, body: ToolRunRequest):
    if default_tool_registry.get(tool_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {tool_id}")
    return await default_tool_registry.run_tool(tool_id, body.input, dry_run=body.dry_run)

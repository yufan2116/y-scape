"""Phase 8 — Tool Hub & Settings integration tests (legacy external adapters)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.integrations.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_list_integrations_returns_six(api_client):
    client, _ = api_client
    res = await client.get("/api/tools/integrations")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    names = {t["name"] for t in data}
    assert "folder_clean" in names


@pytest.mark.asyncio
async def test_integrations_default_not_configured(api_client):
    client, _ = api_client
    res = await client.get("/api/tools/integrations")
    for tool in res.json():
        assert tool["status"] == "not_configured"


@pytest.mark.asyncio
async def test_get_single_integration(api_client):
    client, _ = api_client
    res = await client.get("/api/tools/integrations/folder_clean")
    assert res.status_code == 200
    assert res.json()["toolId"] == "folder_clean"


@pytest.mark.asyncio
async def test_get_unknown_integration(api_client):
    client, _ = api_client
    res = await client.get("/api/tools/integrations/unknown_tool")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_integration_health_check_not_configured(api_client):
    client, _ = api_client
    res = await client.post("/api/tools/integrations/folder_clean/health-check")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "not_configured"


@pytest.mark.asyncio
async def test_integration_health_check_ready_when_paths_exist(api_client, isolated_tool_config, tmp_path):
    project = tmp_path / "folder_clean_proj"
    project.mkdir()
    script = project / "main.py"
    script.write_text("print('ok')", encoding="utf-8")

    client, _ = api_client
    save_res = await client.post(
        "/api/settings/tool-paths",
        json={
            "tool": {
                "tool_id": "folder_clean",
                "project_path": str(project),
                "python_executable": str(Path(__import__("sys").executable)),
                "entry_script": "main.py",
                "enabled": True,
            }
        },
    )
    assert save_res.status_code == 200
    assert save_res.json()["tools"][0]["status"] == "ready"

    hc = await client.post("/api/tools/integrations/folder_clean/health-check")
    assert hc.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_save_tool_paths_persists(api_client, isolated_tool_config, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    client, _ = api_client
    await client.post(
        "/api/settings/tool-paths",
        json={
            "tool": {
                "tool_id": "markdown_convert",
                "project_path": str(project),
                "python_executable": str(Path(__import__("sys").executable)),
                "entry_script": "convert.py",
            }
        },
    )
    cfg_path = isolated_tool_config / "tool_integrations.json"
    assert cfg_path.exists()
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    md = next(t for t in raw["tools"] if t["tool_id"] == "markdown_convert")
    assert md["project_path"] == str(project)


@pytest.mark.asyncio
async def test_integration_run_not_configured(api_client):
    client, _ = api_client
    res = await client.post(
        "/api/tools/integrations/local_rag_query/run",
        json={"input": {"question": "hi", "doc_dir": "."}, "dry_run": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["status"] == "not_configured"


@pytest.mark.asyncio
async def test_tool_registry_lists_adapters(isolated_tool_config):
    reg = ToolRegistry()
    meta = reg.list_metadata()
    names = {m["name"] for m in meta}
    assert "folder_clean" in names
    assert "markdown_convert" in names
    assert "local_rag_query" in names


@pytest.mark.asyncio
async def test_tool_registry_health_check_not_configured(isolated_tool_config):
    reg = ToolRegistry()
    results = await reg.health_check_all()
    folder = next(r for r in results if r["name"] == "folder_clean")
    assert folder["status"] == "not_configured"

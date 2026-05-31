"""Phase 9 — Native Tool Modules."""

from __future__ import annotations

import io
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_list_native_tools(api_client):
    client, _ = api_client
    res = await client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    ids = {t["toolId"] for t in data}
    assert "markdown_convert" in ids
    assert "folder_clean" in ids


@pytest.mark.asyncio
async def test_markdown_convert_txt(api_client, isolated_tool_config, tmp_path, monkeypatch):
    from src.native_tools import artifact_store as art_mod

    art_root = tmp_path / "artifacts"
    monkeypatch.setattr(art_mod.settings, "workspace_root", tmp_path)

    client, _ = api_client
    content = b"Hello native markdown tool"
    res = await client.post(
        "/api/tools/markdown/convert",
        files={"file": ("sample.txt", io.BytesIO(content), "text/plain")},
        data={"source_type": "txt", "output_filename": "converted.md"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["toolId"] == "markdown_convert"
    assert len(body["artifacts"]) >= 2
    names = {a["name"] for a in body["artifacts"]}
    assert "converted.md" in names
    assert "conversion_log.json" in names


@pytest.mark.asyncio
async def test_folder_clean_scan(api_client, isolated_tool_config, tmp_path, monkeypatch):
    from src.native_tools import artifact_store as art_mod

    monkeypatch.setattr(art_mod.settings, "workspace_root", tmp_path)
    scan_dir = tmp_path / "scan_me"
    scan_dir.mkdir()
    (scan_dir / "big.txt").write_text("x" * 100, encoding="utf-8")
    empty = scan_dir / "empty_dir"
    empty.mkdir()

    client, _ = api_client
    res = await client.post(
        "/api/tools/folder-clean/scan",
        json={"target_path": str(scan_dir), "scan_mode": "all", "dry_run": True, "max_depth": 4},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert any(a["name"] == "cleanup_report.md" for a in body["artifacts"])


@pytest.mark.asyncio
async def test_github_resume_generate(api_client, isolated_tool_config, tmp_path, monkeypatch):
    from src.native_tools import artifact_store as art_mod

    monkeypatch.setattr(art_mod.settings, "workspace_root", tmp_path)

    client, _ = api_client
    res = await client.post(
        "/api/tools/github-resume/generate",
        json={
            "repo_url": "https://github.com/octocat/Hello-World",
            "language": "en",
            "role_target": "Backend Engineer",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    names = {a["name"] for a in body["artifacts"]}
    assert "resume_bullets.md" in names
    assert "repo_analysis.json" in names


@pytest.mark.asyncio
async def test_list_tool_artifacts(api_client, isolated_tool_config, tmp_path, monkeypatch):
    from src.native_tools import artifact_store as art_mod

    monkeypatch.setattr(art_mod.settings, "workspace_root", tmp_path)
    client, _ = api_client
    await client.post(
        "/api/tools/github-resume/generate",
        json={"repo_url": "https://github.com/octocat/Hello-World", "language": "zh"},
    )
    res = await client.get("/api/tools/artifacts")
    assert res.status_code == 200
    assert len(res.json()["artifacts"]) >= 1


@pytest.mark.asyncio
async def test_system_settings(api_client, isolated_tool_config):
    client, _ = api_client
    res = await client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "model" in data
    assert "storage" in data
    assert "tool" in data
    assert "runtime" in data

    save = await client.post(
        "/api/settings",
        json={"runtime": {"maxIterations": 10}},
    )
    assert save.status_code == 200
    assert save.json()["runtime"]["maxIterations"] == 10


@pytest.mark.asyncio
async def test_rag_stub(api_client, isolated_tool_config, tmp_path, monkeypatch):
    from src.native_tools import artifact_store as art_mod

    monkeypatch.setattr(art_mod.settings, "workspace_root", tmp_path)
    client, _ = api_client
    res = await client.post(
        "/api/tools/rag/query",
        json={"document_path": str(tmp_path), "question": "What is here?", "top_k": 3},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

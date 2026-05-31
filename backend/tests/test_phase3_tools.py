"""Phase 3 — Tools + Artifact system tests."""

import pytest

from src.agent.runtime_state import RunState
from src.agent.tools import BUILTIN_TOOLS
from src.agent.wal import WalEventType, WalWriter
from src.api.run_event import RunEventType


@pytest.mark.asyncio
async def test_builtin_tools_registered():
    from src.agent.tools import default_tool_registry

    for name in BUILTIN_TOOLS:
        assert default_tool_registry.has(name)


@pytest.mark.asyncio
async def test_execute_tool_wal_pipeline(manager, isolated_runs_dir):
    run_id = await manager.create_task("tool pipeline test")
    result = await manager.execute_tool(run_id, "file_list", {})
    assert result.ok

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.TOOL_INTENT in types
    assert WalEventType.TOOL_STARTED in types
    assert WalEventType.TOOL_COMMITTED in types
    assert WalEventType.TOOL_FAILED not in types


@pytest.mark.asyncio
async def test_execute_tool_timeline_events(manager, isolated_runs_dir):
    run_id = await manager.create_task("timeline tool test")
    await manager.execute_tool(run_id, "web_search", {"query": "agent runtime"})
    from src.api.event_bus import get_or_create_bus

    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    types = [e.type for e in bus.recent()]
    assert RunEventType.TOOL_STARTED in types
    assert RunEventType.TOOL_SUCCEEDED in types


@pytest.mark.asyncio
async def test_web_search_stores_raw_evidence(manager, isolated_runs_dir):
    run_id = await manager.create_task("evidence test")
    await manager.execute_tool(run_id, "web_search", {"query": "test"})
    evidence_path = isolated_runs_dir / run_id / "research_memory" / "raw_evidence.jsonl"
    assert evidence_path.exists()
    assert evidence_path.read_text(encoding="utf-8").count("source_id") >= 3


@pytest.mark.asyncio
async def test_artifact_write_wal_chain(manager, isolated_runs_dir):
    run_id = await manager.create_task("artifact wal test")
    await manager.write_artifact(run_id, "note.md", "# Hello\n\nPhase 3 artifact.", artifact_type="report")

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.FILE_WRITE_INTENT in types
    assert WalEventType.FILE_WRITE_STAGED in types
    assert WalEventType.FILE_WRITE_COMMITTED in types
    assert WalEventType.ARTIFACT_REGISTERED in types


@pytest.mark.asyncio
async def test_artifact_preview_independent_of_status(manager, isolated_runs_dir):
    run_id = await manager.create_task("preview test")
    await manager.write_artifact(run_id, "report.md", "# Report\n\nContent here.", artifact_type="report")

    content = manager.get_artifact_content(run_id, "report.md")
    assert "# Report" in content

    snap = manager.get_status(run_id)
    assert snap is not None
    assert len(snap.artifacts) >= 1


@pytest.mark.asyncio
async def test_file_write_to_artifact_via_tool(manager, isolated_runs_dir):
    run_id = await manager.create_task("tool artifact test")
    await manager.execute_tool(
        run_id,
        "file_write",
        {
            "name": "deliverable.md",
            "content": "# Deliverable\n\nFrom tool.",
            "to_artifact": True,
            "artifact_type": "report",
        },
    )
    assert (isolated_runs_dir / run_id / "artifacts" / "deliverable.md").exists()
    snap = manager.get_status(run_id)
    assert any(a.name == "deliverable.md" for a in snap.artifacts)


@pytest.mark.asyncio
async def test_tool_failure_records_wal(manager, isolated_runs_dir):
    run_id = await manager.create_task("tool fail test")
    result = await manager.execute_tool(run_id, "file_read", {})
    assert not result.ok

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.TOOL_FAILED in types


@pytest.mark.asyncio
async def test_run_tool_api(api_client):
    client, mgr = api_client
    create = await client.post("/api/tasks", json={"goal": "api tool test"})
    run_id = create.json()["runId"]
    resp = await client.post(
        f"/api/tasks/{run_id}/tools/run",
        json={"tool": "finish_task", "params": {"reason": "demo"}},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["ok"] is True


@pytest.mark.asyncio
async def test_artifact_api_preview(api_client):
    client, _mgr = api_client
    create = await client.post("/api/tasks", json={"goal": "artifact api test"})
    run_id = create.json()["runId"]
    write = await client.post(
        f"/api/tasks/{run_id}/artifacts",
        json={"filename": "note.md", "content": "# Note\n\nAPI write.", "artifactType": "report"},
    )
    assert write.status_code == 200
    preview = await client.get(f"/api/tasks/{run_id}/artifacts/note.md")
    assert preview.status_code == 200
    assert "Note" in preview.json()["content"]

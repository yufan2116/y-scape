"""Phase 4 — Demo Mode + Agent Loop tests."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.runtime_state import RunState, is_terminal
from src.agent.wal import WalEventType, WalWriter
from src.api.run_event import RunEventType


async def _wait_terminal(manager, run_id: str, *, timeout: float = 30.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        snap = manager.get_status(run_id)
        if snap and is_terminal(snap.run_state):
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"Run {run_id} did not reach terminal state in {timeout}s")


@pytest.mark.asyncio
async def test_demo_scenarios_list(api_client):
    client, _ = api_client
    resp = await client.get("/api/demo/scenarios")
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert "note_md_demo" in names
    assert "web_research_demo" in names


@pytest.mark.asyncio
async def test_note_md_demo_success(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("note_md_demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS

    content = manager.get_artifact_content(run_id, "note.md")
    assert "笔记" in content or "note" in content.lower()

    from src.api.event_bus import get_or_create_bus

    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    tool_names = [e.tool for e in bus.recent() if e.tool]
    assert "file_write" in tool_names
    assert "finish_task" in tool_names

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.FINALIZE_INTENT in types
    assert WalEventType.FINALIZE_COMMITTED in types


@pytest.mark.asyncio
async def test_web_research_demo_report_length(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("web_research_demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS

    report = manager.get_artifact_content(run_id, "research_report.md")
    assert len(report.replace(" ", "")) >= 800

    from src.api.event_bus import get_or_create_bus

    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    types = [e.type for e in bus.recent()]
    assert RunEventType.RESEARCH_SYNTHESIZED in types


@pytest.mark.asyncio
async def test_summarize_pdf_demo_needs_input(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("summarize_pdf_demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.NEEDS_INPUT
    assert snap.stop_reason == "missing_input"


@pytest.mark.asyncio
async def test_summarize_pdf_demo_with_pdf(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("summarize_pdf_demo")
    pdf_path = isolated_runs_dir / run_id / "workspace" / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS
    summary = manager.get_artifact_content(run_id, "pdf_summary.md")
    assert "PDF" in summary or "摘要" in summary


@pytest.mark.asyncio
async def test_recover_failed_tool_demo(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("recover_failed_tool_demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id, timeout=45.0)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS
    content = manager.get_artifact_content(run_id, "recovery_note.md")
    assert "恢复" in content or "recovery" in content.lower()


@pytest.mark.asyncio
async def test_cancel_task(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("cancel_resume_demo")
    await manager.start_task(run_id)
    await asyncio.sleep(0.2)
    await manager.cancel_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.CANCELLED


@pytest.mark.asyncio
async def test_demo_api_start_flow(api_client):
    client, mgr = api_client
    create = await client.post(
        "/api/tasks/demo",
        json={"scenario": "note_md_demo"},
    )
    assert create.status_code == 200
    run_id = create.json()["runId"]

    start = await client.post(f"/api/tasks/{run_id}/start")
    assert start.status_code == 200
    await _wait_terminal(mgr, run_id)

    status = await client.get(f"/api/tasks/{run_id}/status")
    assert status.json()["runState"] == RunState.SUCCESS.value

    arts = await client.get(f"/api/tasks/{run_id}/artifacts")
    names = {a["name"] for a in arts.json()}
    assert "note.md" in names

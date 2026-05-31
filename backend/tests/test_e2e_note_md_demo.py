"""E2E HTTP test — note_md_demo (mirrors Dashboard Launch Mission)."""

from __future__ import annotations

import pytest

from src.agent.runtime_state import RunState, is_terminal


async def _wait_terminal(client, run_id: str, *, timeout: float = 30.0) -> dict:
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    last: dict = {}
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/tasks/{run_id}/status")
        assert resp.status_code == 200
        last = resp.json()
        if is_terminal(RunState(last["runState"])):
            return last
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Run {run_id} stuck at {last.get('runState')}")


@pytest.mark.asyncio
async def test_e2e_note_md_demo_flow(api_client):
    client, _ = api_client

    created = await client.post("/api/tasks/demo", json={"scenario": "note_md_demo"})
    assert created.status_code == 200, created.text
    run_id = created.json()["runId"]

    started = await client.post(f"/api/tasks/{run_id}/start")
    assert started.status_code == 200, started.text

    final = await _wait_terminal(client, run_id)
    assert final["runState"] == "success"
    names = {a["name"] for a in final.get("artifacts", [])}
    assert "note.md" in names

    events = await client.get(f"/api/tasks/{run_id}/events")
    assert events.status_code == 200
    tools = [e["tool"] for e in events.json() if e.get("tool")]
    assert "file_write" in tools
    assert "finish_task" in tools

    preview = await client.get(f"/api/tasks/{run_id}/artifacts/note.md")
    assert preview.status_code == 200
    assert preview.json().get("content")

"""Phase 11 — E2E demo readiness tests (HTTP layer, no browser)."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.runtime_state import RunState, is_terminal


async def _wait_terminal_api(client, run_id: str, *, timeout: float = 30.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    last: dict = {}
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/tasks/{run_id}/status")
        assert resp.status_code == 200
        last = resp.json()
        if is_terminal(RunState(last["runState"])):
            return last
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Run {run_id} did not finish in {timeout}s (last={last.get('runState')})")


@pytest.mark.asyncio
async def test_e2e_web_research_demo_flow(api_client):
    """Create → start → status → events → artifact preview."""
    client, _mgr = api_client

    created = await client.post("/api/tasks/demo", json={"scenario": "web_research_demo"})
    assert created.status_code == 200
    run_id = created.json()["runId"]

    started = await client.post(f"/api/tasks/{run_id}/start")
    assert started.status_code == 200

    final = await _wait_terminal_api(client, run_id)
    assert final["runState"] == "success"
    assert final.get("artifacts"), "expected artifacts on success"

    events = await client.get(f"/api/tasks/{run_id}/events")
    assert events.status_code == 200
    ev_list = events.json()
    assert len(ev_list) >= 5
    types = {e["type"] for e in ev_list}
    assert "run_started" in types
    assert "run_succeeded" in types

    name = final["artifacts"][0]["name"]
    preview = await client.get(f"/api/tasks/{run_id}/artifacts/{name}")
    assert preview.status_code == 200
    body = preview.json()
    assert body.get("content"), "artifact preview must return content"


@pytest.mark.asyncio
async def test_e2e_status_snapshot_after_reload(api_client):
    """Simulate page refresh: status + events still available."""
    client, _mgr = api_client

    created = await client.post("/api/tasks/demo", json={"scenario": "note_md_demo"})
    run_id = created.json()["runId"]
    await client.post(f"/api/tasks/{run_id}/start")
    await _wait_terminal_api(client, run_id)

    status2 = await client.get(f"/api/tasks/{run_id}/status")
    assert status2.status_code == 200
    snap = status2.json()
    assert snap["runState"] == "success"

    events2 = await client.get(f"/api/tasks/{run_id}/events")
    assert events2.status_code == 200
    assert len(events2.json()) > 0


@pytest.mark.asyncio
async def test_e2e_cancel_during_run(api_client):
    client, _mgr = api_client

    created = await client.post("/api/tasks/demo", json={"scenario": "cancel_resume_demo"})
    run_id = created.json()["runId"]
    await client.post(f"/api/tasks/{run_id}/start")
    await asyncio.sleep(0.2)

    cancelled = await client.post(f"/api/tasks/{run_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"]["runState"] == "cancelled"


@pytest.mark.asyncio
async def test_e2e_recovery_replay_metadata(api_client):
    client, _mgr = api_client

    created = await client.post("/api/tasks/demo", json={"scenario": "web_research_demo"})
    run_id = created.json()["runId"]
    await client.post(f"/api/tasks/{run_id}/start")
    await _wait_terminal_api(client, run_id)

    replay = await client.get(f"/api/tasks/{run_id}/replay")
    assert replay.status_code == 200
    data = replay.json()
    assert "can_retry" in data or "canRetry" in data

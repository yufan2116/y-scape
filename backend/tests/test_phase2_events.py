"""Phase 2 — Event bus + SSE replay tests."""

import pytest
import pytest_asyncio
from unittest.mock import patch

from src.agent.runtime_state import RunState
from src.api.event_bus import EventBus, get_or_create_bus
from src.api.run_event import RunEventType
from src.api.run_manager import RunManager
from src.main import app


@pytest.mark.asyncio
async def test_create_emits_run_started_timeline_event(manager, isolated_runs_dir):
    run_id = await manager.create_task("timeline test")
    run_dir = isolated_runs_dir / run_id
    bus = get_or_create_bus(run_id, run_dir)
    events = bus.recent()
    types = [e.type for e in events]
    assert RunEventType.RUN_STARTED in types
    assert (run_dir / "execution_log.jsonl").exists()


@pytest.mark.asyncio
async def test_transition_emits_state_changed(manager, isolated_runs_dir):
    run_id = await manager.create_task("state changed test")
    await manager.transition(run_id, RunState.PLANNING, step="planning")
    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    types = [e.type for e in bus.recent()]
    assert RunEventType.STATE_CHANGED in types
    assert RunEventType.CHECKPOINT_SAVED in types


@pytest.mark.asyncio
async def test_terminal_transition_emits_run_succeeded(manager, isolated_runs_dir):
    run_id = await manager.create_task("success test")
    await manager.transition(run_id, RunState.SUCCESS, step="done")
    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    types = [e.type for e in bus.recent()]
    assert RunEventType.RUN_SUCCEEDED in types


@pytest.mark.asyncio
async def test_after_event_id_replay_from_buffer(manager, isolated_runs_dir):
    run_id = await manager.create_task("replay buffer test")
    await manager.transition(run_id, RunState.PLANNING)
    await manager.transition(run_id, RunState.THINKING)
    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    all_events = bus.recent()
    pivot = all_events[2].event_id
    replayed = bus.after_event_id(pivot)
    assert len(replayed) >= 1
    assert replayed[0].event_id != pivot


@pytest.mark.asyncio
async def test_after_event_id_replay_from_disk_when_buffer_misses(manager, isolated_runs_dir):
    run_id = await manager.create_task("disk replay test")
    run_dir = isolated_runs_dir / run_id
    for _ in range(3):
        await manager.transition(run_id, RunState.PLANNING)
    bus = get_or_create_bus(run_id, run_dir)
    disk_events = bus.load_all_from_disk()
    pivot = disk_events[0].event_id
    # Simulate empty buffer
    bus._buffer.clear()
    replayed = bus.after_event_id(pivot)
    assert len(replayed) >= 1


@pytest.mark.asyncio
async def test_status_does_not_read_execution_log(manager, isolated_runs_dir):
    run_id = await manager.create_task("status isolation")
    with patch.object(EventBus, "load_all_from_disk", side_effect=AssertionError("status must not read execution log")):
        snap = manager.get_status(run_id)
    assert snap is not None


@pytest.mark.asyncio
async def test_get_events_api(api_client):
    client, _mgr = api_client
    create = await client.post("/api/tasks", json={"goal": "api events test"})
    assert create.status_code == 200
    run_id = create.json()["runId"]
    await client.post(
        f"/api/tasks/{run_id}/transition",
        json={"runState": "planning", "step": "planning"},
    )
    resp = await client.get(f"/api/tasks/{run_id}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["type"] == "run_started" for e in events)


@pytest.mark.asyncio
async def test_events_after_query_param(api_client):
    client, _mgr = api_client
    create = await client.post("/api/tasks", json={"goal": "after param test"})
    run_id = create.json()["runId"]
    first = await client.get(f"/api/tasks/{run_id}/events")
    events = first.json()
    assert len(events) >= 1
    pivot = events[0]["eventId"]
    second = await client.get(f"/api/tasks/{run_id}/events", params={"after": pivot})
    replayed = second.json()
    assert all(e["eventId"] != pivot for e in replayed)


@pytest.mark.asyncio
async def test_audit_log_and_wal_endpoints_separate_from_timeline(manager, isolated_runs_dir):
    run_id = await manager.create_task("audit wal test")
    audit = manager.get_audit_log(run_id)
    wal = manager.get_wal(run_id)
    timeline = manager.get_events(run_id)
    assert len(audit) >= 1
    assert len(wal) >= 1
    assert timeline[0].type == RunEventType.RUN_STARTED
    # WAL uses wal event types, timeline uses run event types
    assert audit[0]["type"] == "run_created"


@pytest.mark.asyncio
async def test_ring_buffer_caps_at_configured_size(isolated_runs_dir, monkeypatch):
    monkeypatch.setattr("src.config.settings.event_buffer_size", 5)
    mgr = RunManager(runs_dir=isolated_runs_dir)
    run_id = await mgr.create_task("ring buffer test")
    run_dir = isolated_runs_dir / run_id
    bus = get_or_create_bus(run_id, run_dir)
    for i in range(10):
        await bus.publish(
            RunEventType.STATE_CHANGED,
            run_state=RunState.PLANNING,
            message=f"event {i}",
        )
    assert len(bus.recent()) <= 5
    assert len(bus.load_all_from_disk()) >= 10

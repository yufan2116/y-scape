"""Phase 1 runtime tests."""

import json
import time
from unittest.mock import patch

import pytest

from src.agent.runtime_state import RunState
from src.agent.tool_registry import default_tool_registry
from src.agent.wal import WalEventType, WalWriter
from src.api.run_manager import RunManager
from src.api.status_snapshot import active_snapshots, snapshot_manager


@pytest.fixture
def manager(isolated_runs_dir):
    active_snapshots.clear()
    return RunManager(runs_dir=isolated_runs_dir)


@pytest.mark.asyncio
async def test_create_task_initializes_run_directory(manager, isolated_runs_dir):
    run_id = await manager.create_task("Phase 1 test goal", demo_mode=True)
    run_dir = isolated_runs_dir / run_id
    assert (run_dir / "wal.jsonl").exists()
    assert (run_dir / "checkpoint.json").exists()
    assert (run_dir / "workspace").is_dir()
    assert (run_dir / "artifacts").is_dir()
    assert (run_dir / "research_memory").is_dir()


@pytest.mark.asyncio
async def test_create_task_writes_wal_and_snapshot(manager, isolated_runs_dir):
    run_id = await manager.create_task("WAL test")
    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    events = wal.read_all()
    types = [e.type for e in events]
    assert WalEventType.RUN_CREATED in types
    assert WalEventType.SNAPSHOT_CREATED in types

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.CREATED
    assert snap.goal == "WAL test"


@pytest.mark.asyncio
async def test_status_hot_path_does_not_read_wal(manager, isolated_runs_dir):
    run_id = await manager.create_task("status perf test")
    with patch.object(WalWriter, "read_all", side_effect=AssertionError("status must not read WAL")):
        snap = manager.get_status(run_id)
    assert snap.run_id == run_id


@pytest.mark.asyncio
async def test_transition_updates_state_wal_checkpoint(manager, isolated_runs_dir):
    run_id = await manager.create_task("transition test")
    snap = await manager.transition(
        run_id,
        RunState.PLANNING,
        step="planning",
        thinking_message="Planning research pipeline",
    )
    assert snap.run_state == RunState.PLANNING
    assert snap.thinking_message == "Planning research pipeline"

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    assert any(e.type == WalEventType.STATE_CHANGED for e in wal.read_all())

    cp = json.loads((isolated_runs_dir / run_id / "checkpoint.json").read_text(encoding="utf-8"))
    assert cp["run_state"] == "planning"
    assert cp["planner_context"]["goal"] == "transition test"


@pytest.mark.asyncio
async def test_terminal_transition_sets_finished_at(manager):
    run_id = await manager.create_task("terminal test")
    snap = await manager.transition(run_id, RunState.SUCCESS, step="completed")
    assert snap.finished_at is not None
    assert snap.progress == 1.0


@pytest.mark.asyncio
async def test_cannot_transition_from_terminal(manager):
    run_id = await manager.create_task("terminal block test")
    await manager.transition(run_id, RunState.SUCCESS)
    with pytest.raises(ValueError, match="terminal"):
        await manager.transition(run_id, RunState.PLANNING)


@pytest.mark.asyncio
async def test_cancellation_token_created(manager):
    run_id = await manager.create_task("cancel token test")
    token = manager.get_cancel_token(run_id)
    assert not token.is_cancelled
    token.cancel()
    assert token.is_cancelled


def test_all_run_states_serializable():
    from src.agent.runtime_state import RUN_STATE_LABELS, RunState

    for state in RunState:
        assert state in RUN_STATE_LABELS
        assert isinstance(state.value, str)


@pytest.mark.asyncio
async def test_status_p95_under_100ms(manager):
    run_id = await manager.create_task("perf test")
    durations = []
    for _ in range(50):
        t0 = time.perf_counter()
        manager.get_status(run_id)
        durations.append((time.perf_counter() - t0) * 1000)
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 < 100, f"status p95={p95:.2f}ms exceeds 100ms target"


@pytest.mark.asyncio
async def test_tool_registry_lists_adapters():
    meta = default_tool_registry.list_metadata()
    names = {m["name"] for m in meta}
    assert "folder_clean" in names
    assert "markdown_convert" in names
    assert "local_rag_query" in names


@pytest.mark.asyncio
async def test_tool_registry_health_check_not_configured():
    results = await default_tool_registry.health_check_all()
    folder = next(r for r in results if r["name"] == "folder_clean")
    assert folder["status"] == "not_configured"

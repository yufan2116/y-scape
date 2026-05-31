"""Phase 7 — Recovery: WAL replay, retry, resume tests."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.runtime_state import RunState, TaskType
from src.agent.wal import WalEventType, WalWriter
from src.agent.wal_replay import replay_run
from src.api.run_event import RunEventType


async def _wait_terminal(manager, run_id: str, *, timeout: float = 45.0) -> None:
    from src.agent.runtime_state import is_terminal

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        snap = manager.get_status(run_id)
        if snap and is_terminal(snap.run_state):
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"Run {run_id} did not reach terminal state")


async def _wait_until(manager, run_id: str, predicate, *, timeout: float = 20.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        result = predicate()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Condition not met")


def test_wal_replay_module_imports():
    from src.agent.wal_replay import WalReplayEngine

    assert WalReplayEngine is not None


@pytest.mark.asyncio
async def test_wal_replay_after_web_search(manager, isolated_runs_dir):
    run_id = await manager.create_task("replay test", demo_mode=True)
    await manager.execute_tool(run_id, "web_search", {"query": "agent"})
    replayed = replay_run(run_id, isolated_runs_dir)
    assert "web_search" in replayed.completed_steps
    assert (isolated_runs_dir / run_id / "research_memory" / "raw_evidence.jsonl").exists()


@pytest.mark.asyncio
async def test_interrupt_and_resume_during_slow_step(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("cancel_resume_demo")
    await manager.start_task(run_id)
    await asyncio.sleep(0.3)
    await manager.interrupt_task(run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.INTERRUPTED

    replayed = replay_run(run_id, isolated_runs_dir)
    assert replayed.can_resume

    await manager.resume_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.WAL_REPLAY_STARTED in types
    assert WalEventType.CHECKPOINT_RESTORED in types
    assert WalEventType.WAL_REPLAY_COMPLETED in types


@pytest.mark.asyncio
async def test_retry_after_quality_blocked(manager, isolated_runs_dir, monkeypatch):
    from src.agent.deliverable_quality import QualityBlockedError
    from src.agent.report_writer import ReportWriter

    run_id = await manager.create_demo_task("web_research_demo")
    original_write = ReportWriter.write

    def always_short(self, synthesis, *, goal, force_short=False):
        return original_write(self, synthesis, goal=goal, force_short=True)

    monkeypatch.setattr(ReportWriter, "write", always_short)

    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.QUALITY_BLOCKED

    monkeypatch.setattr(ReportWriter, "write", original_write)
    await manager.retry_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS


@pytest.mark.asyncio
async def test_replay_revision_attempt_from_checkpoint(manager, isolated_runs_dir):
    """WAL replay picks up revision_attempt from checkpoint after quality failure."""
    run_id = await manager.create_demo_task("quality_failure_then_revision")
    await manager.start_task(run_id)

    async def quality_failed_once() -> bool:
        from src.api.event_bus import get_or_create_bus

        bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
        return RunEventType.QUALITY_CHECK_FAILED in [e.type for e in bus.recent()]

    await _wait_until(manager, run_id, quality_failed_once, timeout=25.0)

    record = manager.get_record(run_id)
    if record and record.run_state == RunState.SUCCESS:
        replayed = replay_run(run_id, isolated_runs_dir)
        assert replayed.revision_attempt >= 1
        assert replayed.quality_passed
        return

    await manager.interrupt_task(run_id)
    replayed = replay_run(run_id, isolated_runs_dir)
    assert replayed.revision_attempt >= 1
    assert replayed.can_resume

    await manager.resume_task(run_id)
    await _wait_terminal(manager, run_id)
    assert manager.get_status(run_id).run_state == RunState.SUCCESS


@pytest.mark.asyncio
async def test_retry_resume_api(api_client):
    client, mgr = api_client
    run_id = await mgr.create_task("api retry", demo_mode=True)
    await mgr.transition(run_id, RunState.FAILED, step="failed", stop_reason="test")

    retry = await client.post(f"/api/tasks/{run_id}/retry")
    assert retry.status_code == 200

    run_id2 = await mgr.create_demo_task("note_md_demo")
    await mgr.start_task(run_id2)
    await _wait_terminal(mgr, run_id2)

    replay = await client.get(f"/api/tasks/{run_id2}/replay")
    assert replay.status_code == 200
    assert replay.json()["can_resume"] is False

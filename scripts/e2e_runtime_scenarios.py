#!/usr/bin/env python3
"""Phase 1 E2E — runtime skeleton validation only."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT / "src"))

from src.agent.runtime_state import RunState
from src.api.run_manager import RunManager
from src.api.status_snapshot import active_snapshots


async def phase1_smoke() -> None:
    active_snapshots.clear()
    mgr = RunManager(runs_dir=Path("runs_active"))
    run_id = await mgr.create_task("Phase 1 E2E smoke test", demo_mode=True)
    snap = await mgr.transition(run_id, RunState.PLANNING, step="planning")
    assert snap.run_state == RunState.PLANNING
    status = mgr.get_status(run_id)
    assert status is not None
    print(f"[OK] phase1_smoke run_id={run_id} state={status.run_state.value}")


if __name__ == "__main__":
    asyncio.run(phase1_smoke())

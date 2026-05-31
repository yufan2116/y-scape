"""Recovery service — WAL replay + resume/retry helpers (Phase 7)."""

from __future__ import annotations

from pathlib import Path

from src.agent.checkpoint import CheckpointStore
from src.agent.wal_replay import ReplayedRunState, WalReplayEngine


class RecoveryService:
    @staticmethod
    def load_replay(run_dir: Path, run_id: str | None = None) -> ReplayedRunState:
        return WalReplayEngine.replay(run_dir, run_id)

    @staticmethod
    def load_checkpoint(run_dir: Path):
        return CheckpointStore(run_dir).load()

    @staticmethod
    def can_resume(ctx: ReplayedRunState) -> bool:
        return ctx.can_resume

    @staticmethod
    def can_retry(ctx: ReplayedRunState) -> bool:
        return ctx.can_retry

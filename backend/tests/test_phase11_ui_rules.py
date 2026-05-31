"""Unit tests for frontend recovery button rules (mirrors runState.ts)."""

from __future__ import annotations

import pytest

# Mirror of frontend/src/lib/runState.ts logic for QA regression
TERMINAL = {
    "success", "degraded_success", "failed", "cancelled", "timeout",
    "needs_input", "stale", "interrupted", "quality_blocked",
}


def can_cancel(state: str) -> bool:
    return state not in TERMINAL


def can_resume(state: str) -> bool:
    return state in {"interrupted", "stale", "tool_failed"}


def can_retry(state: str) -> bool:
    return state in {"failed", "timeout", "quality_blocked"}


def can_start_new(state: str | None) -> bool:
    return state in {"success", "degraded_success"}


@pytest.mark.parametrize("state", ["thinking", "tool_running", "planning"])
def test_running_shows_cancel(state):
    assert can_cancel(state)
    assert not can_start_new(state)


def test_failed_shows_retry_only():
    assert can_retry("failed")
    assert not can_resume("failed")


@pytest.mark.parametrize("state", ["interrupted", "stale"])
def test_interrupted_stale_shows_resume(state):
    assert can_resume(state)
    assert not can_retry(state)


def test_success_shows_start_new():
    assert can_start_new("success")
    assert not can_cancel("success")
    assert not can_retry("success")

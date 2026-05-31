"""Phase 6 — Deliverable Quality Gate tests."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.deliverable_quality import DeliverableQualityGate, QualityBlockedError
from src.agent.report_writer import ReportWriter
from src.agent.research_memory import ResearchMemoryStore, SynthesisResult, Source, SourceType
from src.agent.runtime_state import RunState, TaskType
from src.agent.synthesis_engine import SynthesisEngine
from src.agent.wal import WalEventType, WalWriter
from src.api.run_event import RunEventType


async def _wait_terminal(manager, run_id: str, *, timeout: float = 30.0) -> None:
    from src.agent.runtime_state import is_terminal

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        snap = manager.get_status(run_id)
        if snap and is_terminal(snap.run_state):
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"Run {run_id} did not reach terminal state")


def _sample_synthesis() -> SynthesisResult:
    return SynthesisResult(
        executive_summary="针对 Agent Runtime 的综合分析摘要，涵盖可观测性与恢复能力。",
        key_trends=["WAL 事务语义", "Timeline 事件流", "质量门控"],
        important_papers=["论文 A [source:src_001]"],
        industry_news=["新闻 B"],
        risks=["质量未通过不能 success"],
        future_directions=["Phase 7 Recovery"],
        sources=[
            Source(title="S1", url="https://example.com/1", type=SourceType.WEB),
            Source(title="S2", url="https://example.com/2", type=SourceType.WEB),
            Source(title="S3", url="https://example.com/3", type=SourceType.WEB),
        ],
    )


def test_quality_gate_rejects_short_report():
    gate = DeliverableQualityGate.for_task(TaskType.RESEARCH_REPORT)
    short = ReportWriter().write(_sample_synthesis(), goal="测试", force_short=True)
    result = gate.validate(short, source_ids=["src_001", "src_002", "src_003"])
    assert not result.passed
    assert any("字数" in f or "章节" in f for f in result.failures)


def test_quality_gate_passes_full_report():
    gate = DeliverableQualityGate.for_task(TaskType.RESEARCH_REPORT)
    full = ReportWriter().write(_sample_synthesis(), goal="Agent Runtime 质量测试")
    result = gate.validate(
        full,
        source_ids=["src_001", "src_002", "src_003"],
        filename="research_report.md",
    )
    assert result.passed
    assert result.body_chars >= 800


@pytest.mark.asyncio
async def test_synthesis_pipeline_includes_quality_wal(manager, isolated_runs_dir):
    run_id = await manager.create_task("quality wal", demo_mode=True, task_type=TaskType.RESEARCH_REPORT)
    await manager.execute_tool(run_id, "web_search", {"query": "agent"})
    await manager.synthesize_and_write_report(run_id)

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.QUALITY_CHECK_STARTED in types
    assert WalEventType.QUALITY_CHECK_PASSED in types


@pytest.mark.asyncio
async def test_quality_failure_then_revision_demo(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("quality_failure_then_revision")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS
    assert snap.revision_attempt >= 1

    from src.api.event_bus import get_or_create_bus

    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    types = [e.type for e in bus.recent()]
    assert RunEventType.QUALITY_CHECK_FAILED in types
    assert RunEventType.QUALITY_CHECK_PASSED in types
    assert RunEventType.QUALITY_REVISION_STARTED in types

    report = manager.get_artifact_content(run_id, "research_report.md")
    assert len(report.replace(" ", "").replace("\n", "")) >= 800


@pytest.mark.asyncio
async def test_quality_circuit_breaker(manager, isolated_runs_dir, monkeypatch):
    run_id = await manager.create_task(
        "circuit breaker",
        demo_mode=True,
        task_type=TaskType.RESEARCH_REPORT,
    )
    await manager.execute_tool(run_id, "web_search", {"query": "test"})

    original_write = ReportWriter.write

    def always_short(self, synthesis, *, goal, force_short=False):
        return original_write(self, synthesis, goal=goal, force_short=True)

    monkeypatch.setattr(ReportWriter, "write", always_short)

    with pytest.raises(QualityBlockedError):
        await manager.synthesize_and_write_report(run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.QUALITY_BLOCKED

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    assert WalEventType.QUALITY_CIRCUIT_BREAKER_TRIGGERED in [e.type for e in wal.read_all()]

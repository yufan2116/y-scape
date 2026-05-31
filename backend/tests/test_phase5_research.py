"""Phase 5 — Research Memory + SynthesisEngine + ReportWriter tests."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.report_writer import ReportWriter
from src.agent.research_memory import ResearchMemoryStore, SynthesisResult
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


@pytest.mark.asyncio
async def test_research_memory_extracts_findings(isolated_runs_dir):
    run_dir = isolated_runs_dir / "run_mem"
    run_dir.mkdir()
    (run_dir / "research_memory").mkdir()
    memory = ResearchMemoryStore(run_dir)
    memory.append_raw_evidence(
        {
            "source_id": "src_001",
            "title": "Agent Runtime",
            "url": "https://example.com/a",
            "content": "长时运行 Agent 需要 WAL 与 Checkpoint。",
        }
    )
    findings = memory.ensure_findings()
    assert len(findings) == 1
    assert findings[0].source == "src_001"
    assert (run_dir / "research_memory" / "findings.jsonl").exists()


@pytest.mark.asyncio
async def test_synthesis_engine_produces_result(isolated_runs_dir):
    run_dir = isolated_runs_dir / "run_syn"
    run_dir.mkdir()
    memory = ResearchMemoryStore(run_dir)
    memory.append_raw_evidence(
        {
            "source_id": "src_001",
            "title": "Observability",
            "url": "https://example.com/b",
            "content": "Agent Runtime observability patterns.",
        }
    )
    memory.append_raw_evidence(
        {
            "source_id": "src_002",
            "title": "Recovery",
            "url": "https://example.com/c",
            "content": "Checkpoint recovery for agents.",
        }
    )
    engine = SynthesisEngine(demo_mode=True)
    result = await engine.synthesize(memory, goal="Agent Runtime 架构")
    assert isinstance(result, SynthesisResult)
    assert result.executive_summary
    assert len(result.key_trends) >= 3
    assert len(result.sources) >= 2
    assert memory.has_synthesis()


@pytest.mark.asyncio
async def test_report_writer_required_sections(isolated_runs_dir):
    run_dir = isolated_runs_dir / "run_writer"
    run_dir.mkdir()
    memory = ResearchMemoryStore(run_dir)
    memory.append_raw_evidence(
        {
            "source_id": "src_001",
            "title": "Test",
            "content": "Content for synthesis test.",
        }
    )
    synthesis = await SynthesisEngine(demo_mode=True).synthesize(memory, goal="测试目标")
    report = ReportWriter().write(synthesis, goal="测试目标")
    for heading in (
        "## 摘要",
        "## 近期论文",
        "## 近期新闻",
        "## 技术趋势",
        "## 产业影响",
        "## 风险与挑战",
        "## 未来方向",
        "## 参考来源",
    ):
        assert heading in report
    assert len(report.replace(" ", "").replace("\n", "")) >= 800


@pytest.mark.asyncio
async def test_synthesis_pipeline_wal_events(manager, isolated_runs_dir):
    run_id = await manager.create_task("synthesis wal test", demo_mode=True)
    await manager.execute_tool(run_id, "web_search", {"query": "agent"})
    await manager.synthesize_and_write_report(run_id, "research_report.md")

    wal = WalWriter(isolated_runs_dir / run_id, run_id)
    types = [e.type for e in wal.read_all()]
    assert WalEventType.RESEARCH_SYNTHESIS_STARTED in types
    assert WalEventType.RESEARCH_FINDINGS_EXTRACTED in types
    assert WalEventType.RESEARCH_SYNTHESIS_COMMITTED in types
    assert WalEventType.ARTIFACT_REGISTERED in types

    from src.api.event_bus import get_or_create_bus

    bus = get_or_create_bus(run_id, isolated_runs_dir / run_id)
    assert RunEventType.RESEARCH_SYNTHESIZED in [e.type for e in bus.recent()]


@pytest.mark.asyncio
async def test_research_report_blocked_without_synthesis(manager):
    run_id = await manager.create_task(
        "block direct write",
        demo_mode=True,
        task_type=TaskType.RESEARCH_REPORT,
    )
    result = await manager.execute_tool(
        run_id,
        "file_write",
        {
            "name": "research_report.md",
            "content": "# Skip synthesis\n",
            "to_artifact": True,
        },
    )
    assert not result.ok
    assert "synthesis" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_web_research_demo_uses_synthesis_pipeline(manager, isolated_runs_dir):
    run_id = await manager.create_demo_task("web_research_demo")
    await manager.start_task(run_id)
    await _wait_terminal(manager, run_id)

    snap = manager.get_status(run_id)
    assert snap is not None
    assert snap.run_state == RunState.SUCCESS

    memory = ResearchMemoryStore(isolated_runs_dir / run_id)
    assert memory.has_findings()
    assert memory.has_synthesis()

    report = manager.get_artifact_content(run_id, "research_report.md")
    assert "## 技术趋势" in report
    assert len(report.replace(" ", "").replace("\n", "")) >= 800

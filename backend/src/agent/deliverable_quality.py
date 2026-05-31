"""Deliverable Quality Gate — file write ≠ task success (Phase 6)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.agent.runtime_state import TaskType


@dataclass
class QualityPolicy:
    min_body_chars: int = 800
    required_sections: list[str] = field(
        default_factory=lambda: [
            "摘要",
            "近期论文",
            "近期新闻",
            "技术趋势",
            "产业影响",
            "风险与挑战",
            "未来方向",
            "参考来源",
        ]
    )
    min_sources: int = 3
    max_quality_failures: int = 3
    require_title: bool = True


RESEARCH_REPORT_POLICY = QualityPolicy()
SIMPLE_NOTE_POLICY = QualityPolicy(
    min_body_chars=10,
    required_sections=[],
    min_sources=0,
    require_title=True,
)


class QualityResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    body_chars: int = 0
    section_count: int = 0
    source_count: int = 0


class DeliverableQualityGate:
    """Validates deliverables before a run may finalize as success."""

    def __init__(self, policy: QualityPolicy | None = None) -> None:
        self.policy = policy or RESEARCH_REPORT_POLICY

    @classmethod
    def for_task(cls, task_type: TaskType) -> "DeliverableQualityGate":
        if task_type == TaskType.RESEARCH_REPORT:
            return cls(RESEARCH_REPORT_POLICY)
        if task_type in {TaskType.SIMPLE_NOTE, TaskType.TECHNICAL_REPORT, TaskType.CODE_OUTPUT}:
            return cls(SIMPLE_NOTE_POLICY)
        return cls(RESEARCH_REPORT_POLICY)

    def validate(
        self,
        content: str,
        *,
        source_ids: list[str] | None = None,
        filename: str = "research_report.md",
    ) -> QualityResult:
        if not filename.endswith(".md"):
            return QualityResult(passed=True, body_chars=len(content))

        failures: list[str] = []
        body_chars = len(content.replace(" ", "").replace("\n", ""))

        if body_chars < self.policy.min_body_chars:
            failures.append(
                f"正文字数 {body_chars} 低于最低要求 {self.policy.min_body_chars}"
            )

        if self.policy.require_title and not re.search(r"^#\s+.+\n", content, re.MULTILINE):
            failures.append("缺少 Markdown 标题 (# 标题)")

        for section in self.policy.required_sections:
            pattern = rf"^##\s*{re.escape(section)}\s*$"
            if not re.search(pattern, content, re.MULTILINE):
                failures.append(f"缺少必需章节: {section}")

        for section in self._find_empty_sections(content):
            failures.append(f"空章节: {section}")

        source_refs = len(re.findall(r"\[source:[^\]]+\]", content, re.IGNORECASE))
        ref_lines = len(re.findall(r"^-\s+\[", content, re.MULTILINE))
        listed_sources = len(source_ids or [])
        effective_sources = max(listed_sources, source_refs, ref_lines)
        if effective_sources < self.policy.min_sources:
            failures.append(
                f"引用来源数 {effective_sources} 低于最低要求 {self.policy.min_sources}"
            )

        section_count = len(re.findall(r"^#{1,3}\s+.+\s*$", content, re.MULTILINE))
        return QualityResult(
            passed=len(failures) == 0,
            failures=failures,
            body_chars=body_chars,
            section_count=section_count,
            source_count=effective_sources,
        )

    def _find_empty_sections(self, content: str) -> list[str]:
        empty: list[str] = []
        blocks = re.split(r"(?=^##\s+)", content, flags=re.MULTILINE)
        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue
            first_line = stripped.splitlines()[0]
            if not first_line.startswith("##"):
                continue
            lines = [ln for ln in stripped.splitlines() if ln.strip()]
            if len(lines) <= 1:
                title = lines[0].lstrip("#").strip()
                if title:
                    empty.append(title)
        return empty


class QualityBlockedError(Exception):
    """Raised when quality circuit breaker triggers."""

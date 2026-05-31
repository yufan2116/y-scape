"""Research memory — layered evidence, findings, synthesis persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    WEB = "web"
    PDF = "pdf"
    SCRAPE = "scrape"
    RAG = "rag"
    FILE = "file"


class Source(BaseModel):
    title: str
    url: str | None = None
    type: SourceType = SourceType.WEB
    publisher: str | None = None
    date: datetime | None = None


class Finding(BaseModel):
    title: str
    summary: str
    source: str
    url: str | None = None
    date: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.8


class RawEvidence(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    content: str
    collected_at: datetime | None = None


class SynthesisResult(BaseModel):
    executive_summary: str = ""
    key_trends: list[str] = Field(default_factory=list)
    important_papers: list[str] = Field(default_factory=list)
    industry_news: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    future_directions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class ResearchMemoryStore:
    """Persist research layers under runs_active/{runId}/research_memory/."""

    def __init__(self, run_dir: Path) -> None:
        self.base = run_dir / "research_memory"
        self.base.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.base / "raw_evidence.jsonl"
        self.findings_path = self.base / "findings.jsonl"
        self.synthesis_path = self.base / "synthesis_result.json"

    def has_raw_evidence(self) -> bool:
        return self.raw_path.exists() and bool(self.raw_path.read_text(encoding="utf-8").strip())

    def has_findings(self) -> bool:
        return self.findings_path.exists() and bool(self.findings_path.read_text(encoding="utf-8").strip())

    def has_synthesis(self) -> bool:
        return self.synthesis_path.exists()

    def append_raw_evidence(self, item: dict[str, Any]) -> None:
        record = {**item, "collected_at": item.get("collected_at") or _utcnow().isoformat()}
        with open(self.raw_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def load_raw_evidence(self) -> list[RawEvidence]:
        if not self.raw_path.exists():
            return []
        items: list[RawEvidence] = []
        for line in self.raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            collected = data.get("collected_at")
            if isinstance(collected, str):
                try:
                    data["collected_at"] = datetime.fromisoformat(collected.replace("Z", "+00:00"))
                except ValueError:
                    data["collected_at"] = None
            items.append(RawEvidence.model_validate(data))
        return items

    def _infer_source_type(self, evidence: RawEvidence) -> SourceType:
        sid = evidence.source_id.lower()
        if sid.startswith("pdf_"):
            return SourceType.PDF
        if sid.startswith("scrape_"):
            return SourceType.SCRAPE
        return SourceType.WEB

    def extract_findings_from_raw(self) -> list[Finding]:
        findings: list[Finding] = []
        for ev in self.load_raw_evidence():
            source_type = self._infer_source_type(ev)
            tags = ["research", source_type.value]
            if "agent" in ev.content.lower() or "runtime" in ev.content.lower():
                tags.append("agent_runtime")
            findings.append(
                Finding(
                    title=ev.title,
                    summary=ev.content[:240].strip(),
                    source=ev.source_id,
                    url=ev.url,
                    date=ev.collected_at,
                    tags=tags,
                    confidence=0.85,
                )
            )
        return findings

    def save_findings(self, findings: list[Finding]) -> None:
        lines = [f.model_dump_json() + "\n" for f in findings]
        self.findings_path.write_text("".join(lines), encoding="utf-8")

    def load_findings(self) -> list[Finding]:
        if not self.findings_path.exists():
            return []
        items: list[Finding] = []
        for line in self.findings_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(Finding.model_validate_json(line))
        return items

    def ensure_findings(self) -> list[Finding]:
        existing = self.load_findings()
        if existing:
            return existing
        findings = self.extract_findings_from_raw()
        if findings:
            self.save_findings(findings)
        return findings

    def build_sources(self, findings: list[Finding]) -> list[Source]:
        seen: set[str] = set()
        sources: list[Source] = []
        raw_by_id = {e.source_id: e for e in self.load_raw_evidence()}
        for f in findings:
            if f.source in seen:
                continue
            seen.add(f.source)
            raw = raw_by_id.get(f.source)
            stype = self._infer_source_type(raw) if raw else SourceType.WEB
            sources.append(
                Source(
                    title=f.title,
                    url=f.url,
                    type=stype,
                    publisher="demo" if stype == SourceType.WEB else None,
                    date=f.date,
                )
            )
        return sources

    def save_synthesis(self, result: SynthesisResult) -> None:
        self.synthesis_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_synthesis(self) -> SynthesisResult | None:
        if not self.synthesis_path.exists():
            return None
        return SynthesisResult.model_validate_json(self.synthesis_path.read_text(encoding="utf-8"))

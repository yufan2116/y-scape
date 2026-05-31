"""Native tool artifact store — outputs for built-in Tool Hub modules."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NativeArtifactMeta:
    name: str
    type: str
    url: str
    size: int
    job_id: str
    tool_id: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "size": self.size,
            "jobId": self.job_id,
            "toolId": self.tool_id,
            "createdAt": self.created_at.isoformat(),
        }


class NativeArtifactStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (settings.workspace_root / "tool_artifacts")
        self.root.mkdir(parents=True, exist_ok=True)

    def create_job(self, tool_id: str) -> str:
        job_id = f"{tool_id}_{uuid.uuid4().hex[:10]}"
        (self.root / job_id).mkdir(parents=True, exist_ok=True)
        return job_id

    def write_text(
        self,
        job_id: str,
        tool_id: str,
        filename: str,
        content: str,
        *,
        artifact_type: str = "file",
    ) -> NativeArtifactMeta:
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return self._meta(path, job_id, tool_id, artifact_type)

    def write_bytes(
        self,
        job_id: str,
        tool_id: str,
        filename: str,
        data: bytes,
        *,
        artifact_type: str = "file",
    ) -> NativeArtifactMeta:
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / filename
        path.write_bytes(data)
        return self._meta(path, job_id, tool_id, artifact_type)

    def read_text(self, job_id: str, filename: str) -> str:
        path = self._resolve(job_id, filename)
        return path.read_text(encoding="utf-8")

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self.root.exists():
            return items
        for job_dir in sorted(self.root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not job_dir.is_dir():
                continue
            job_id = job_dir.name
            tool_id = job_id.rsplit("_", 1)[0] if "_" in job_id else "unknown"
            for path in sorted(job_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(job_dir).as_posix()
                stat = path.stat()
                items.append(
                    {
                        "name": rel,
                        "type": _guess_type(rel),
                        "url": f"/api/tools/artifacts/{job_id}/{rel}",
                        "size": stat.st_size,
                        "jobId": job_id,
                        "toolId": tool_id,
                        "createdAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    }
                )
            if len(items) >= limit:
                break
        return items[:limit]

    def _meta(self, path: Path, job_id: str, tool_id: str, artifact_type: str) -> NativeArtifactMeta:
        stat = path.stat()
        name = path.relative_to(self.root / job_id).as_posix()
        return NativeArtifactMeta(
            name=name,
            type=artifact_type,
            url=f"/api/tools/artifacts/{job_id}/{name}",
            size=stat.st_size,
            job_id=job_id,
            tool_id=tool_id,
            created_at=_utcnow(),
        )

    def _resolve(self, job_id: str, filename: str) -> Path:
        if ".." in filename or filename.startswith("/"):
            raise ValueError("invalid filename")
        path = (self.root / job_id / filename).resolve()
        job_root = (self.root / job_id).resolve()
        if not str(path).startswith(str(job_root)):
            raise ValueError("path traversal denied")
        if not path.is_file():
            raise FileNotFoundError(filename)
        return path


def _guess_type(name: str) -> str:
    lower = name.lower()
    if lower.endswith((".md", ".markdown")):
        return "markdown"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".txt"):
        return "text"
    return "file"


def tool_response(
    *,
    ok: bool,
    tool_id: str,
    message: str = "",
    artifacts: list[NativeArtifactMeta] | None = None,
    data: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {"ok": ok, "toolId": tool_id}
    if ok:
        body["message"] = message
        body["artifacts"] = [a.to_dict() for a in (artifacts or [])]
        body["data"] = data or {}
    else:
        body["error"] = error or message
    return body

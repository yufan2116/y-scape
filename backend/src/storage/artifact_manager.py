"""Artifact manager — WAL-integrated staged writes (Phase 3)."""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.agent.wal import WalEventType, WalWriter
from src.api.status_snapshot import ArtifactMeta


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactManager:
    """Staged file writes: INTENT → STAGED → COMMITTED → ARTIFACT_REGISTERED."""

    def __init__(self, run_dir: Path, run_id: str, wal: WalWriter) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.wal = wal
        self.root = run_dir / "artifacts"
        self.staging = run_dir / "workspace" / ".staging"
        self.root.mkdir(parents=True, exist_ok=True)
        self.staging.mkdir(parents=True, exist_ok=True)

    def write_artifact(
        self,
        filename: str,
        content: str,
        *,
        artifact_type: str = "file",
    ) -> ArtifactMeta:
        self.wal.append(
            WalEventType.FILE_WRITE_INTENT,
            payload={"filename": filename, "size": len(content)},
        )
        staging_path = self.staging / filename
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path.write_text(content, encoding="utf-8")
        self.wal.append(
            WalEventType.FILE_WRITE_STAGED,
            payload={"filename": filename, "staging_path": str(staging_path)},
        )

        target = self.root / filename
        try:
            if target.exists():
                target.unlink()
            shutil.move(str(staging_path), str(target))
            self.wal.append(
                WalEventType.FILE_WRITE_COMMITTED,
                payload={"filename": filename, "path": str(target)},
            )
        except OSError as exc:
            self.wal.append(
                WalEventType.FILE_WRITE_FAILED,
                payload={"filename": filename, "error": str(exc)},
            )
            raise

        meta = self._build_meta(target, artifact_type=artifact_type)
        self.wal.append(
            WalEventType.ARTIFACT_REGISTERED,
            payload={
                "artifact_id": f"art_{uuid.uuid4().hex[:12]}",
                **meta.model_dump(by_alias=True, mode="json"),
            },
        )
        return meta

    def read_artifact(self, filename: str) -> str:
        path = self.root / filename
        if not path.exists():
            raise FileNotFoundError(filename)
        return path.read_text(encoding="utf-8")

    def artifact_exists(self, filename: str) -> bool:
        return (self.root / filename).is_file()

    def _build_meta(self, path: Path, *, artifact_type: str) -> ArtifactMeta:
        stat = path.stat()
        name = path.name
        return ArtifactMeta(
            name=name,
            type=artifact_type,
            path=str(path),
            url=f"/api/tasks/{self.run_id}/artifacts/{name}",
            size=stat.st_size,
            createdAt=_utcnow(),
        )

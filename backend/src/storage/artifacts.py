"""Artifact storage — independent of run status."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from src.api.status_snapshot import ArtifactMeta


class ArtifactStore:
    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.root = run_dir / "artifacts"
        self.staging = run_dir / "workspace" / ".staging"
        self.root.mkdir(parents=True, exist_ok=True)
        self.staging.mkdir(parents=True, exist_ok=True)

    def stage_and_commit(self, filename: str, content: str) -> ArtifactMeta:
        staging_path = self.staging / filename
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path.write_text(content, encoding="utf-8")
        target = self.root / filename
        if target.exists():
            target.unlink()
        shutil.move(str(staging_path), str(target))
        return self._meta_for(target, artifact_type="report")

    def read_artifact(self, filename: str) -> str:
        path = self.root / filename
        if not path.exists():
            raise FileNotFoundError(filename)
        return path.read_text(encoding="utf-8")

    def list_meta(self) -> list[ArtifactMeta]:
        return list_artifact_meta(self.run_id, self.run_dir)

    def _meta_for(self, path: Path, *, artifact_type: str) -> ArtifactMeta:
        stat = path.stat()
        name = path.name
        return ArtifactMeta(
            name=name,
            type=artifact_type,
            path=str(path),
            url=f"/api/tasks/{self.run_id}/artifacts/{name}",
            size=stat.st_size,
            createdAt=datetime.utcfromtimestamp(stat.st_mtime),
        )


def list_artifact_meta(run_id: str, run_dir: Path) -> list[ArtifactMeta]:
    root = run_dir / "artifacts"
    if not root.exists():
        return []
    items: list[ArtifactMeta] = []
    for path in sorted(root.iterdir()):
        if path.is_file():
            stat = path.stat()
            ext = path.suffix.lower()
            atype = "report" if ext in {".md", ".markdown"} else "file"
            items.append(
                ArtifactMeta(
                    name=path.name,
                    type=atype,
                    path=str(path),
                    url=f"/api/tasks/{run_id}/artifacts/{path.name}",
                    size=stat.st_size,
                    createdAt=datetime.utcfromtimestamp(stat.st_mtime),
                )
            )
    return items

"""Workspace file operations."""

from __future__ import annotations

from pathlib import Path


class WorkspaceStore:
    def __init__(self, run_dir: Path) -> None:
        self.root = run_dir / "workspace"
        self.root.mkdir(parents=True, exist_ok=True)

    def list_files(self) -> list[dict]:
        files: list[dict] = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and ".staging" not in p.parts:
                rel = p.relative_to(self.root).as_posix()
                files.append({"name": rel, "size": p.stat().st_size})
        return files

    def read_file(self, name: str) -> str:
        path = self._resolve(name)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(name)
        return path.read_text(encoding="utf-8")

    def write_file(self, name: str, content: str) -> Path:
        path = self._resolve(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _resolve(self, name: str) -> Path:
        target = (self.root / name).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            raise ValueError("path traversal denied")
        return target

"""Folder clean — dry_run scan only, never deletes files."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.native_tools.artifact_store import NativeArtifactMeta, NativeArtifactStore, tool_response

TOOL_ID = "folder_clean"


def _safe_target(path_str: str) -> Path | None:
    if not path_str.strip():
        return None
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        return None
    return p


def _scan(
    root: Path,
    *,
    scan_mode: str,
    max_depth: int,
    large_file_mb: float = 50.0,
) -> dict[str, Any]:
    empty_dirs: list[str] = []
    large_files: list[dict[str, Any]] = []
    hash_map: dict[str, list[str]] = defaultdict(list)
    file_count = 0
    dir_count = 0

    large_threshold = large_file_mb * 1024 * 1024

    def walk_dir(current: Path, depth: int) -> None:
        nonlocal file_count, dir_count
        if depth > max_depth:
            return
        try:
            entries = list(current.iterdir())
        except OSError:
            return

        has_file = False
        for entry in entries:
            if entry.is_file():
                has_file = True
                file_count += 1
                rel = entry.relative_to(root).as_posix()
                size = entry.stat().st_size
                if size >= large_threshold:
                    large_files.append({"path": rel, "sizeBytes": size, "sizeMb": round(size / (1024 * 1024), 2)})
                if scan_mode in {"duplicates", "all"}:
                    try:
                        h = hashlib.md5()
                        with entry.open("rb") as f:
                            for chunk in iter(lambda: f.read(65536), b""):
                                h.update(chunk)
                        hash_map[h.hexdigest()].append(rel)
                    except OSError:
                        pass
            elif entry.is_dir():
                dir_count += 1
                walk_dir(entry, depth + 1)

        if not has_file and not any(e.is_dir() for e in entries) and depth > 0:
            empty_dirs.append(current.relative_to(root).as_posix())

    walk_dir(root, 0)

    duplicates = [
        {"hash": h, "files": paths}
        for h, paths in hash_map.items()
        if len(paths) > 1
    ]

    return {
        "targetPath": str(root),
        "scanMode": scan_mode,
        "maxDepth": max_depth,
        "dryRun": True,
        "fileCount": file_count,
        "dirCount": dir_count,
        "emptyDirs": empty_dirs if scan_mode in {"empty_dirs", "all"} else [],
        "largeFiles": large_files if scan_mode in {"large_files", "all"} else [],
        "duplicates": duplicates if scan_mode in {"duplicates", "all"} else [],
    }


def _report_md(result: dict[str, Any]) -> str:
    lines = [
        "# Folder Clean Report",
        "",
        f"- **Target:** `{result['targetPath']}`",
        f"- **Mode:** {result['scanMode']}",
        f"- **Max depth:** {result['maxDepth']}",
        f"- **Dry run:** yes (no files deleted)",
        "",
        f"Scanned **{result['fileCount']}** files in **{result['dirCount']}** directories.",
        "",
    ]

    if result["emptyDirs"]:
        lines += ["## Empty Directories", ""]
        for d in result["emptyDirs"][:100]:
            lines.append(f"- `{d}`")
        if len(result["emptyDirs"]) > 100:
            lines.append(f"- … and {len(result['emptyDirs']) - 100} more")
        lines.append("")

    if result["largeFiles"]:
        lines += ["## Large Files", ""]
        for f in result["largeFiles"][:50]:
            lines.append(f"- `{f['path']}` — {f['sizeMb']} MB")
        lines.append("")

    if result["duplicates"]:
        lines += ["## Duplicate Groups", ""]
        for group in result["duplicates"][:20]:
            lines.append(f"### Hash `{group['hash'][:8]}…`")
            for p in group["files"]:
                lines.append(f"- `{p}`")
            lines.append("")

    return "\n".join(lines)


async def scan_folder(
    store: NativeArtifactStore,
    *,
    target_path: str,
    scan_mode: str = "all",
    dry_run: bool = True,
    max_depth: int = 8,
) -> dict[str, Any]:
    target = _safe_target(target_path)
    if target is None:
        return tool_response(ok=False, tool_id=TOOL_ID, error=f"Target path not found: {target_path}")

    if not target.is_dir():
        return tool_response(ok=False, tool_id=TOOL_ID, error="Target must be a directory")

    mode = scan_mode if scan_mode in {"empty_dirs", "large_files", "duplicates", "all"} else "all"
    depth = max(1, min(max_depth, 32))

    result = _scan(target, scan_mode=mode, max_depth=depth)
    result["dryRun"] = dry_run

    job_id = store.create_job(TOOL_ID)
    artifacts: list[NativeArtifactMeta] = []
    artifacts.append(
        store.write_text(job_id, TOOL_ID, "cleanup_report.md", _report_md(result), artifact_type="markdown")
    )
    artifacts.append(
        store.write_text(
            job_id,
            TOOL_ID,
            "cleanup_candidates.json",
            json.dumps(result, indent=2, ensure_ascii=False),
            artifact_type="json",
        )
    )

    return tool_response(
        ok=True,
        tool_id=TOOL_ID,
        message=f"Scan complete — {len(result['emptyDirs'])} empty dirs, {len(result['duplicates'])} duplicate groups",
        artifacts=artifacts,
        data=result,
    )

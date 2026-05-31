"""Stub implementations for P1 native tools."""

from __future__ import annotations

import json
from typing import Any

from src.native_tools.artifact_store import NativeArtifactStore, tool_response


async def stub_rag_query(
    store: NativeArtifactStore,
    *,
    document_path: str,
    question: str,
    top_k: int = 5,
    model: str = "ollama",
) -> dict[str, Any]:
    job_id = store.create_job("local_rag_query")
    answer = f"# RAG Stub Answer\n\n**Question:** {question}\n\n**Doc path:** `{document_path}`\n\n*Local RAG module coming soon — stub response only.*"
    citations = {"citations": [], "topK": top_k, "model": model, "status": "stub"}
    arts = [
        store.write_text(job_id, "local_rag_query", "answer.md", answer, artifact_type="markdown"),
        store.write_text(job_id, "local_rag_query", "citations.json", json.dumps(citations, indent=2), artifact_type="json"),
    ]
    return tool_response(
        ok=True,
        tool_id="local_rag_query",
        message="Stub RAG query — full indexing not yet implemented",
        artifacts=arts,
        data={"stub": True},
    )


async def stub_bilibili_download(
    store: NativeArtifactStore,
    *,
    url: str,
    output_dir: str,
    quality: str = "1080p",
) -> dict[str, Any]:
    job_id = store.create_job("bilibili_download")
    meta = {"url": url, "outputDir": output_dir, "quality": quality, "status": "stub"}
    log = f"# Bilibili Download Stub\n\nURL: {url}\nOutput: {output_dir}\nQuality: {quality}\n\n*Download module coming soon.*"
    arts = [
        store.write_text(job_id, "bilibili_download", "download_log.md", log, artifact_type="markdown"),
        store.write_text(job_id, "bilibili_download", "video_metadata.json", json.dumps(meta, indent=2), artifact_type="json"),
    ]
    return tool_response(
        ok=True,
        tool_id="bilibili_download",
        message="Stub download — Bilibili integration coming soon",
        artifacts=arts,
        data=meta,
    )


async def stub_quickforge_run(
    store: NativeArtifactStore,
    *,
    script: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    job_id = store.create_job("quickforge_launcher")
    run_log = {
        "script": script,
        "args": args or [],
        "stdout": "[stub] Script execution not yet wired",
        "stderr": "",
        "status": "stub",
    }
    arts = [
        store.write_text(job_id, "quickforge_launcher", "run_log.json", json.dumps(run_log, indent=2), artifact_type="json"),
        store.write_text(job_id, "quickforge_launcher", "stdout.txt", run_log["stdout"], artifact_type="text"),
    ]
    return tool_response(
        ok=True,
        tool_id="quickforge_launcher",
        message="Stub launcher — script runner coming soon",
        artifacts=arts,
        data=run_log,
    )

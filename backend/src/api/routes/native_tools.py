"""Native Tool Hub API — built-in modules with artifact output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.native_tools.artifact_store import NativeArtifactStore
from src.native_tools.folder_clean import scan_folder
from src.native_tools.github_resume import generate_resume
from src.native_tools.markdown import convert_markdown
from src.native_tools.registry import get_native_tool, list_native_tools
from src.native_tools.stubs import stub_bilibili_download, stub_quickforge_run, stub_rag_query

router = APIRouter(prefix="/api/tools", tags=["native-tools"])


def _store() -> NativeArtifactStore:
    return NativeArtifactStore()


class FolderCleanRequest(BaseModel):
    target_path: str
    scan_mode: str = "all"
    dry_run: bool = True
    max_depth: int = Field(default=8, ge=1, le=32)


class GitHubResumeRequest(BaseModel):
    repo_url: str
    language: str = "zh"
    role_target: str = ""


class RagQueryRequest(BaseModel):
    document_path: str
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    model: str = "ollama"


class BilibiliDownloadRequest(BaseModel):
    url: str
    output_dir: str = "./downloads"
    quality: str = "1080p"


class QuickForgeRunRequest(BaseModel):
    script: str
    args: list[str] = Field(default_factory=list)


@router.get("/native")
async def list_tools_native():
    store = NativeArtifactStore()
    tools = list_native_tools()
    recent = store.list_recent(limit=30)
    for tool in tools:
        tool["recentArtifacts"] = [a for a in recent if a.get("toolId") == tool["toolId"]][:5]
    return tools


@router.get("/native/{tool_id}")
async def get_tool_native(tool_id: str):
    tool = get_native_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_id}")
    recent = NativeArtifactStore().list_recent(limit=20)
    tool["recentArtifacts"] = [a for a in recent if a.get("toolId") == tool_id]
    return tool


@router.get("/artifacts")
async def list_tool_artifacts():
    return {"artifacts": NativeArtifactStore().list_recent(limit=100)}


@router.get("/artifacts/{job_id}/{filename:path}")
async def get_tool_artifact(job_id: str, filename: str) -> dict[str, Any]:
    store = NativeArtifactStore()
    try:
        content = store.read_text(job_id, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    lower = filename.lower()
    if lower.endswith((".md", ".markdown")):
        content_type = "text/markdown"
    elif lower.endswith(".json"):
        content_type = "application/json"
    else:
        content_type = "text/plain"
    return {"name": filename, "content": content, "contentType": content_type, "jobId": job_id}


@router.post("/markdown/convert")
async def markdown_convert(
    file: UploadFile = File(...),
    source_type: str = Form(""),
    output_filename: str = Form(""),
):
    raw = await file.read()
    filename = file.filename or "upload.txt"
    return await convert_markdown(
        _store(),
        file_bytes=raw,
        filename=filename,
        source_type=source_type or Path(filename).suffix.lstrip("."),
        output_filename=output_filename,
    )


@router.post("/folder-clean/scan")
async def folder_clean_scan(body: FolderCleanRequest):
    return await scan_folder(
        _store(),
        target_path=body.target_path,
        scan_mode=body.scan_mode,
        dry_run=body.dry_run,
        max_depth=body.max_depth,
    )


@router.post("/github-resume/generate")
async def github_resume_generate(body: GitHubResumeRequest):
    return await generate_resume(
        _store(),
        repo_url=body.repo_url,
        language=body.language,
        role_target=body.role_target,
    )


@router.post("/rag/query")
async def rag_query(body: RagQueryRequest):
    return await stub_rag_query(
        _store(),
        document_path=body.document_path,
        question=body.question,
        top_k=body.top_k,
        model=body.model,
    )


@router.post("/bilibili/download")
async def bilibili_download(body: BilibiliDownloadRequest):
    return await stub_bilibili_download(
        _store(),
        url=body.url,
        output_dir=body.output_dir,
        quality=body.quality,
    )


@router.post("/quickforge/run")
async def quickforge_run(body: QuickForgeRunRequest):
    return await stub_quickforge_run(_store(), script=body.script, args=body.args)

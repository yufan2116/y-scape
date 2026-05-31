"""Native tool registry metadata."""

from __future__ import annotations

from typing import Any, Literal

ToolAvailability = Literal["available", "stub", "coming_soon"]

NATIVE_TOOLS: list[dict[str, Any]] = [
    {
        "toolId": "markdown_convert",
        "name": "Markdown Toolkit",
        "category": "Research Tools",
        "description": "PDF / DOCX / HTML / TXT 转 Markdown",
        "status": "available",
        "inputSummary": "Upload file · source type · output name",
    },
    {
        "toolId": "folder_clean",
        "name": "Folder Clean",
        "category": "File Tools",
        "description": "扫描文件夹 · 空目录 · 重复文件 · 大文件 · dry_run 建议",
        "status": "available",
        "inputSummary": "Target path · scan mode · max depth",
    },
    {
        "toolId": "github_resume_generator",
        "name": "GitHub Resume Generator",
        "category": "Portfolio Tools",
        "description": "GitHub 仓库 → STAR 简历 bullet（中/英）",
        "status": "available",
        "inputSummary": "Repo URL · language · role target",
    },
    {
        "toolId": "local_rag_query",
        "name": "Local RAG",
        "category": "Research Tools",
        "description": "本地文档索引与问答",
        "status": "stub",
        "inputSummary": "Document path · question · top_k",
    },
    {
        "toolId": "bilibili_download",
        "name": "Bilibili Download",
        "category": "Media Tools",
        "description": "B 站视频信息获取与下载",
        "status": "stub",
        "inputSummary": "URL / BV · output dir · quality",
    },
    {
        "toolId": "quickforge_launcher",
        "name": "QuickForge Launcher",
        "category": "Automation Tools",
        "description": "脚本管理与启动",
        "status": "stub",
        "inputSummary": "Script · args · run",
    },
]


def list_native_tools() -> list[dict[str, Any]]:
    return [dict(t) for t in NATIVE_TOOLS]


def get_native_tool(tool_id: str) -> dict[str, Any] | None:
    for tool in NATIVE_TOOLS:
        if tool["toolId"] == tool_id:
            return dict(tool)
    return None

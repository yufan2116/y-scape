"""Built-in tools — Phase 3 unified ToolResult contract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from src.agent.research_memory import ResearchMemoryStore
from src.config import settings
from src.storage.workspace import WorkspaceStore

BUILTIN_TOOLS = (
    "file_list",
    "file_read",
    "file_write",
    "pdf_extract",
    "web_search",
    "web_scrape",
    "finish_task",
)

DEMO_SEARCH_RESULTS = [
    {
        "source_id": "src_001",
        "title": "Agent Runtime 可观测性",
        "url": "https://example.com/observability",
        "snippet": "长时运行 Agent 需要结构化事件流与轻量 status API，Timeline 可审计且无需解析原始日志。",
    },
    {
        "source_id": "src_002",
        "title": "可恢复执行模式",
        "url": "https://example.com/recovery",
        "snippet": "基于 Checkpoint 的恢复可跳过已完成步骤。质量门控防止文件写入被误判为任务成功。",
    },
    {
        "source_id": "src_003",
        "title": "研究综合流水线",
        "url": "https://example.com/synthesis",
        "snippet": "报告必须来自 ranked facts 的综合，而非 raw search HTML。Context pack 限制 LLM 输入规模。",
    },
]


@dataclass
class ToolResult:
    ok: bool
    tool: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"ok": self.ok, "tool": self.tool, "output": self.output}
        if self.error:
            data["error"] = self.error
        return data


@dataclass
class ToolContext:
    run_id: str
    run_dir: Path
    goal: str
    workspace: WorkspaceStore

    @property
    def research_memory_dir(self) -> Path:
        p = self.run_dir / "research_memory"
        p.mkdir(parents=True, exist_ok=True)
        return p


ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler

    def has(self, name: str) -> bool:
        return name in self._handlers

    def list_tools(self) -> list[str]:
        return sorted(self._handlers.keys())

    async def execute(
        self,
        name: str,
        params: dict[str, Any],
        ctx: ToolContext,
    ) -> ToolResult:
        handler = self._handlers.get(name)
        if not handler:
            return ToolResult(ok=False, tool=name, output={}, error=f"Unknown tool: {name}")
        try:
            return await asyncio.wait_for(
                handler(params, ctx),
                timeout=settings.tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ToolResult(ok=False, tool=name, output={}, error="tool timeout")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return ToolResult(ok=False, tool=name, output={}, error=str(exc))


def _append_raw_evidence(ctx: ToolContext, item: dict[str, Any]) -> None:
    ResearchMemoryStore(ctx.run_dir).append_raw_evidence(item)


def build_builtin_registry() -> ToolRegistry:
    reg = ToolRegistry()

    async def file_list(_params: dict, ctx: ToolContext) -> ToolResult:
        files = ctx.workspace.list_files()
        return ToolResult(ok=True, tool="file_list", output={"files": files})

    async def file_read(params: dict, ctx: ToolContext) -> ToolResult:
        name = params.get("path") or params.get("name", "")
        if not name:
            return ToolResult(ok=False, tool="file_read", output={}, error="missing path")
        try:
            content = ctx.workspace.read_file(name)
            return ToolResult(ok=True, tool="file_read", output={"path": name, "content": content})
        except FileNotFoundError:
            return ToolResult(ok=False, tool="file_read", output={}, error=f"not found: {name}")

    async def file_write(params: dict, ctx: ToolContext) -> ToolResult:
        name = params.get("path") or params.get("name", "notes.txt")
        content = params.get("content", "")
        if not content and content != "":
            return ToolResult(ok=False, tool="file_write", output={}, error="missing content")
        path = ctx.workspace.write_file(name, content)
        rel = path.resolve().relative_to(ctx.run_dir.resolve()).as_posix()
        return ToolResult(
            ok=True,
            tool="file_write",
            output={"path": rel, "size": len(content), "workspace": True},
        )

    async def pdf_extract(params: dict, ctx: ToolContext) -> ToolResult:
        pdf_path = params.get("path", "report.pdf")
        text = (
            f"[demo pdf_extract: {pdf_path}] "
            "本段为 Phase 3 演示提取文本。真实 PDF 解析将在后续接入。"
        )
        _append_raw_evidence(
            ctx,
            {
                "source_id": f"pdf_{hash(pdf_path) % 10000:04d}",
                "title": f"PDF: {pdf_path}",
                "url": None,
                "content": text,
            },
        )
        return ToolResult(
            ok=True,
            tool="pdf_extract",
            output={"path": pdf_path, "text": text, "pages": 3},
        )

    async def web_search(params: dict, ctx: ToolContext) -> ToolResult:
        query = params.get("query") or ctx.goal
        results = [{**r, "query": query} for r in DEMO_SEARCH_RESULTS]
        for item in results:
            _append_raw_evidence(
                ctx,
                {
                    "source_id": item["source_id"],
                    "title": item["title"],
                    "url": item.get("url"),
                    "content": item.get("snippet", ""),
                },
            )
        return ToolResult(ok=True, tool="web_search", output={"query": query, "results": results})

    async def web_scrape(params: dict, ctx: ToolContext) -> ToolResult:
        url = params.get("url", "https://example.com")
        text = f"[demo scrape: {url}] Agent Runtime 结合规划、工具调用与质量门控。"
        _append_raw_evidence(
            ctx,
            {
                "source_id": f"scrape_{hash(url) % 10000:04d}",
                "title": f"Scraped: {url}",
                "url": url,
                "content": text,
            },
        )
        return ToolResult(ok=True, tool="web_scrape", output={"url": url, "text": text})

    async def finish_task(params: dict, _ctx: ToolContext) -> ToolResult:
        reason = params.get("reason", "tool requested finish")
        return ToolResult(ok=True, tool="finish_task", output={"finished": True, "reason": reason})

    reg.register("file_list", file_list)
    reg.register("file_read", file_read)
    reg.register("file_write", file_write)
    reg.register("pdf_extract", pdf_extract)
    reg.register("web_search", web_search)
    reg.register("web_scrape", web_scrape)
    reg.register("finish_task", finish_task)
    return reg


default_tool_registry = build_builtin_registry()

"""Task API — Phase 1–4: tasks, events, demo agent loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.runtime_state import RunState, TaskType, is_terminal
from src.api.event_bus import get_or_create_bus, get_bus
from src.api.run_manager import run_manager
from src.config import settings
from src.demo.scenarios import list_scenarios

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
demo_router = APIRouter(prefix="/api/demo", tags=["demo"])


class CreateTaskRequest(BaseModel):
    goal: str
    demo_mode: bool | None = Field(default=None, alias="demoMode")
    task_type: str = Field(default="research_report", alias="taskType")

    model_config = {"populate_by_name": True}


class CreateDemoTaskRequest(BaseModel):
    scenario: str
    goal: str | None = None

    model_config = {"populate_by_name": True}


class TransitionRequest(BaseModel):
    run_state: str = Field(alias="runState")
    step: str | None = None
    thinking_message: str | None = Field(default=None, alias="thinkingMessage")

    model_config = {"populate_by_name": True}


class RunToolRequest(BaseModel):
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class WriteArtifactRequest(BaseModel):
    filename: str
    content: str
    artifact_type: str = Field(default="file", alias="artifactType")

    model_config = {"populate_by_name": True}


def _ensure_run_exists(run_id: str) -> None:
    if not run_manager.get_status(run_id):
        raise HTTPException(status_code=404, detail=f"Task {run_id} not found")


@router.post("")
async def create_task(body: CreateTaskRequest) -> dict[str, Any]:
    try:
        task_type = TaskType(body.task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid taskType: {body.task_type}")
    run_id = await run_manager.create_task(
        body.goal,
        demo_mode=body.demo_mode,
        task_type=task_type,
    )
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.post("/demo")
async def create_demo_task(body: CreateDemoTaskRequest) -> dict[str, Any]:
    try:
        run_id = await run_manager.create_demo_task(body.scenario, goal=body.goal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    snap = run_manager.get_status(run_id)
    return {
        "runId": run_id,
        "scenario": body.scenario,
        "status": snap.model_dump(by_alias=True, mode="json") if snap else {},
    }


@router.post("/{run_id}/start")
async def start_task(run_id: str) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        await run_manager.start_task(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.post("/{run_id}/cancel")
async def cancel_task(run_id: str) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    await run_manager.cancel_task(run_id)
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.post("/{run_id}/retry")
async def retry_task(run_id: str) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        await run_manager.retry_task(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.post("/{run_id}/resume")
async def resume_task(run_id: str) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        await run_manager.resume_task(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.post("/{run_id}/interrupt")
async def interrupt_task(run_id: str) -> dict[str, Any]:
    """Simulate crash — cooperative interrupt for recovery demo."""
    _ensure_run_exists(run_id)
    await run_manager.interrupt_task(run_id)
    snap = run_manager.get_status(run_id)
    return {"runId": run_id, "status": snap.model_dump(by_alias=True, mode="json") if snap else {}}


@router.get("/{run_id}/replay")
async def get_replay_state(run_id: str) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        replayed = run_manager.get_replay_state(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return replayed.model_dump(mode="json")


@demo_router.get("/scenarios")
async def get_demo_scenarios() -> list[dict[str, str]]:
    return list_scenarios()


@router.get("/{run_id}/status")
async def get_status(run_id: str) -> dict[str, Any]:
    snap = run_manager.get_status(run_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Task {run_id} not found")
    return snap.model_dump(by_alias=True, mode="json")


@router.get("/{run_id}/events")
async def get_events(
    run_id: str,
    after: str | None = None,
    after_event_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    _ensure_run_exists(run_id)
    after_id = after or after_event_id
    events = run_manager.get_events(run_id, after_event_id=after_id, limit=limit)
    return [e.model_dump(by_alias=True, mode="json") for e in events]


@router.get("/{run_id}/events/stream")
async def stream_events(
    run_id: str,
    request: Request,
    last_event_id: str | None = None,
):
    _ensure_run_exists(run_id)
    run_dir = run_manager.runs_dir / run_id
    bus = get_or_create_bus(run_id, run_dir)
    after_id = last_event_id or request.headers.get("Last-Event-ID")

    async def generator():
        backlog = bus.after_event_id(after_id)
        for event in backlog:
            data = event.model_dump(by_alias=True, mode="json")
            yield f"id: {event.event_id}\nevent: {event.type.value}\ndata: {json.dumps(data, default=str)}\n\n"

        snap = run_manager.get_status(run_id)
        if snap and is_terminal(snap.run_state) and not backlog:
            yield _done_chunk(run_id, snap.run_state.value)
            return

        queue = bus.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=settings.sse_heartbeat_seconds)
                except asyncio.TimeoutError:
                    snap = run_manager.get_status(run_id)
                    if snap and is_terminal(snap.run_state):
                        yield _done_chunk(run_id, snap.run_state.value)
                        break
                    yield ": heartbeat\n\n"
                    continue

                if event is None:
                    snap = run_manager.get_status(run_id)
                    state = snap.run_state.value if snap else "unknown"
                    yield _done_chunk(run_id, state)
                    break

                data = event.model_dump(by_alias=True, mode="json")
                yield f"id: {event.event_id}\nevent: {event.type.value}\ndata: {json.dumps(data, default=str)}\n\n"

                if event.type.value.startswith("run_") and event.type.value not in {"run_started"}:
                    yield _done_chunk(run_id, event.run_state.value)
                    break
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _done_chunk(run_id: str, state: str) -> str:
    payload = json.dumps({"runId": run_id, "state": state, "done": True})
    return f"event: done\ndata: {payload}\n\n"


@router.get("/{run_id}/audit-log")
async def get_audit_log(run_id: str, limit: int = 500) -> list[dict[str, Any]]:
    """Layer B — audit / debug only, not for Timeline UI."""
    _ensure_run_exists(run_id)
    entries = run_manager.get_audit_log(run_id)
    return entries[-limit:]


@router.get("/{run_id}/wal")
async def get_wal(run_id: str, limit: int = 500) -> list[dict[str, Any]]:
    """WAL for recovery — not for Timeline UI."""
    _ensure_run_exists(run_id)
    entries = run_manager.get_wal(run_id)
    return entries[-limit:]


@router.post("/{run_id}/tools/run")
async def run_tool(run_id: str, body: RunToolRequest) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        result = await run_manager.execute_tool(run_id, body.tool, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    snap = run_manager.get_status(run_id)
    return {
        "result": result.to_dict(),
        "status": snap.model_dump(by_alias=True, mode="json") if snap else {},
    }


@router.get("/{run_id}/artifacts")
async def list_artifacts(run_id: str) -> list[dict[str, Any]]:
    _ensure_run_exists(run_id)
    items = run_manager.list_artifacts(run_id)
    return [a.model_dump(by_alias=True, mode="json") for a in items]


@router.get("/{run_id}/artifacts/{filename}")
async def get_artifact_content(run_id: str, filename: str) -> dict[str, Any]:
    """Independent preview — file exists → content; else 404."""
    run_dir = run_manager.runs_dir / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Task {run_id} not found")
    try:
        content = run_manager.get_artifact_content(run_id, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Artifact {filename} not found")
    content_type = "text/markdown" if filename.lower().endswith((".md", ".markdown")) else "text/plain"
    return {"name": filename, "content": content, "contentType": content_type}


@router.post("/{run_id}/artifacts")
async def write_artifact(run_id: str, body: WriteArtifactRequest) -> dict[str, Any]:
    _ensure_run_exists(run_id)
    try:
        meta = await run_manager.write_artifact(
            run_id,
            body.filename,
            body.content,
            artifact_type=body.artifact_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return meta.model_dump(by_alias=True, mode="json")


@router.post("/{run_id}/transition")
async def transition_state(run_id: str, body: TransitionRequest) -> dict[str, Any]:
    """Dev endpoint — state machine + timeline event validation."""
    try:
        new_state = RunState(body.run_state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid runState: {body.run_state}")
    try:
        snap = await run_manager.transition(
            run_id,
            new_state,
            step=body.step,
            thinking_message=body.thinking_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return snap.model_dump(by_alias=True, mode="json")

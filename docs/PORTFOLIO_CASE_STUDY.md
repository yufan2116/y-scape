# Portfolio Case Study — Y.Scape

## Problem

Long-running AI agents need more than chat: they need **observability**, **recovery**, and **deliverable quality verification**.

## Solution

Y.Scape implements an Agent Runtime with:

- **Lightweight status API** — in-memory snapshots, P95 < 100ms
- **Event-driven Timeline** — SSE with replay and ring buffer
- **Research pipeline** — evidence → synthesis → report (no raw search-to-file shortcut)
- **Quality gate** — file write ≠ task success; circuit breaker after 3 failures
- **Demo mode** — full portfolio demo without real LLM costs

## Demo Flow (Interview)

1. Start backend + frontend
2. Click **Quality Failure → Revision**
3. Show Timeline: quality_check_failed then quality_check_passed
4. Preview `research_report.md` via independent artifact API
5. Open `runs_active/{runId}/execution_log.jsonl` for audit narrative

## Differentiators vs Chatbot Demo

| Chatbot | Y.Scape Runtime |
|---------|-----------------|
| Message history = state | Snapshot + event log |
| Done when model stops | Done when quality gate passes |
| Opaque tool calls | Structured tool_started/succeeded/failed |
| No recovery | Checkpoint + resume |

## Tech Stack

Python FastAPI · asyncio · React · TypeScript · Vite · SSE · local filesystem

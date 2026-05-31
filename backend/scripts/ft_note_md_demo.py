"""Functional test: note_md_demo API chain (mirrors frontend Launch Mission)."""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import httpx

BASE = "http://localhost:8000"
SCENARIO = "note_md_demo"


def log(step: str, **fields: Any) -> None:
    print(f"\n{'=' * 60}\n### {step}\n{'=' * 60}")
    for k, v in fields.items():
        if k == "body" and isinstance(v, (dict, list)):
            print(f"{k}:\n{json.dumps(v, ensure_ascii=False, indent=2)[:4000]}")
        else:
            print(f"{k}: {v}")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=60.0)
    failures: list[str] = []

    # Step 0 — scenarios (Dashboard load)
    url = "/api/demo/scenarios"
    try:
        r = client.get(url)
        log("0 GET scenarios", url=f"{BASE}{url}", status=r.status_code, body=r.json() if r.is_success else r.text)
        if r.status_code != 200:
            failures.append("A/C: scenarios list failed")
        elif SCENARIO not in {s["name"] for s in r.json()}:
            failures.append(f"C: scenario {SCENARIO} missing")
    except Exception as exc:
        log("0 GET scenarios ERROR", url=f"{BASE}{url}", error=str(exc))
        failures.append("A: cannot reach backend")
        print("\nSUMMARY:", failures)
        return 1

    # Step 1 — POST demo (createDemoTask)
    url = "/api/tasks/demo"
    body = {"scenario": SCENARIO}
    try:
        r = client.post(url, json=body)
        log(
            "1 POST create demo",
            url=f"{BASE}{url}",
            status=r.status_code,
            request_body=body,
            body=r.json() if r.content else r.text,
        )
        if r.status_code != 200:
            failures.append("B: POST /api/tasks/demo failed")
            print("\nSUMMARY:", failures)
            return 1
        run_id = r.json()["runId"]
        initial_state = r.json().get("status", {}).get("runState")
    except Exception as exc:
        log("1 POST create demo ERROR", error=str(exc))
        failures.append("A/B: create demo request failed")
        print("\nSUMMARY:", failures)
        return 1

  # Step 2 — POST start
    url = f"/api/tasks/{run_id}/start"
    try:
        r = client.post(url)
        log(
            "2 POST start",
            url=f"{BASE}{url}",
            status=r.status_code,
            body=r.json() if r.content else r.text,
        )
        if r.status_code != 200:
            failures.append("B/C: POST start failed")
    except Exception as exc:
        log("2 POST start ERROR", error=str(exc))
        failures.append("B: start request failed")

    # Step 3 — poll status
    url = f"/api/tasks/{run_id}/status"
    final_snap: dict = {}
    for i in range(120):
        time.sleep(0.15)
        r = client.get(url)
        if r.status_code != 200:
            log(f"3.{i} GET status FAIL", url=f"{BASE}{url}", status=r.status_code, body=r.text)
            failures.append("D: status polling HTTP error")
            break
        snap = r.json()
        state = snap.get("runState")
        if i in (0, 1, 2) or state in ("success", "failed", "cancelled", "timeout", "needs_input"):
            log(
                f"3.{i} GET status",
                url=f"{BASE}{url}",
                status=r.status_code,
                runState=state,
                thinking=snap.get("thinkingMessage"),
                artifacts=snap.get("artifacts"),
            )
        final_snap = snap
        if state in ("success", "failed", "cancelled", "timeout", "needs_input", "quality_blocked"):
            break
    else:
        failures.append("D/C: status never reached terminal")

    if final_snap.get("runState") != "success":
        failures.append(f"C: expected success, got {final_snap.get('runState')} err={final_snap.get('error')}")

    # Step 4 — events
    url = f"/api/tasks/{run_id}/events"
    r = client.get(url)
    events = r.json() if r.is_success else []
    types = [e.get("type") for e in events]
    tools = [e.get("tool") for e in events if e.get("tool")]
    log(
        "4 GET events",
        url=f"{BASE}{url}",
        status=r.status_code,
        event_count=len(events),
        types=types,
        tools=tools,
    )
    if r.status_code != 200:
        failures.append("E: events fetch failed")
    elif len(events) < 3:
        failures.append("E: too few events")

    has_file_write = "file_write" in tools or any(
        e.get("type") == "tool_succeeded" and e.get("tool") == "file_write" for e in events
    )
    has_finish_task = "finish_task" in tools
    has_planner = any(t in types for t in ("planner_started", "planner_response"))
    has_thinking = bool(final_snap.get("thinkingMessage")) or any(
        e.get("message") for e in events if e.get("type") == "planner_response"
    )

    # Step 5 — artifacts list from status
    arts = final_snap.get("artifacts") or []
    names = [a.get("name") for a in arts]
    log("5 Artifacts from status", names=names)
    if "note.md" not in names:
        failures.append("F: note.md not in status artifacts")

    # Step 6 — preview
    url = f"/api/tasks/{run_id}/artifacts/note.md"
    r = client.get(url)
    preview = r.json() if r.is_success else {}
    log(
        "6 GET artifact preview",
        url=f"{BASE}{url}",
        status=r.status_code,
        contentType=preview.get("contentType"),
        content_len=len(preview.get("content") or ""),
        body_preview=(preview.get("content") or "")[:200],
    )
    if r.status_code != 200:
        failures.append("G: preview API failed")
    elif not preview.get("content"):
        failures.append("G: preview empty")

    # Checklist mapping
    print("\n" + "=" * 60)
    print("CHECKLIST (API-level)")
    print("=" * 60)
    print(f"runId present: {bool(run_id)} -> {run_id}")
    print(f"runState terminal: {final_snap.get('runState')} (initial was {initial_state})")
    print(f"Timeline events: {len(events)} types")
    print(f"Thinking content: {has_thinking}")
    print(f"file_write in tool events: {has_file_write}")
    print(f"finish_task in tool events: {has_finish_task} (demo uses action=finish, not finish_task tool)")
    print(f"note.md in artifacts: {'note.md' in names}")
    print(f"preview OK: {r.status_code == 200 and bool(preview.get('content'))}")

    if failures:
        print("\nFAILURES:", failures)
        # Layer guess
        layer = "unknown"
        if "POST /api/tasks/demo" in str(failures) or "create demo" in str(failures):
            layer = "B"
        elif "start" in str(failures):
            layer = "B/C"
        elif "status" in str(failures):
            layer = "D"
        elif "events" in str(failures):
            layer = "E"
        elif "note.md not" in str(failures):
            layer = "F"
        elif "preview" in str(failures):
            layer = "G"
        elif "success" in str(failures):
            layer = "C"
        print("LIKELY LAYER:", layer)
        return 1

    print("\nALL API CHECKS PASSED for note_md_demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())

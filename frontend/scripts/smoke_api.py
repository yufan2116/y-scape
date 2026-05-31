"""Quick API smoke test for Phase 9 frontend integration."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
TERMINAL = {
    "success",
    "degraded_success",
    "failed",
    "cancelled",
    "timeout",
    "quality_blocked",
    "interrupted",
    "needs_input",
    "stale",
}


def req(method: str, path: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    scenarios = req("GET", "/api/demo/scenarios")
    assert isinstance(scenarios, list) and scenarios, "no scenarios"
    print(f"scenarios: {len(scenarios)}")

    created = req("POST", "/api/tasks/demo", {"scenario": "web_research_demo"})
    run_id = created["runId"]
    print(f"runId: {run_id}")

    started = req("POST", f"/api/tasks/{run_id}/start")
    assert "status" in started

    st: dict = {}
    for _ in range(120):
        st = req("GET", f"/api/tasks/{run_id}/status")  # type: ignore[assignment]
        if st["runState"] in TERMINAL:
            break
        time.sleep(0.25)
    else:
        print("timeout waiting terminal", st.get("runState"))
        return 1

    print(f"final: {st['runState']} progress={st.get('progress')}")

    events = req("GET", f"/api/tasks/{run_id}/events")
    assert isinstance(events, list) and events, "no events"
    print(f"events: {len(events)}")

    arts = st.get("artifacts") or []
    print(f"artifacts: {[a['name'] for a in arts]}")
    if arts:
        name = arts[0]["name"]
        preview = req("GET", f"/api/tasks/{run_id}/artifacts/{name}")
        assert preview.get("content"), "empty preview"
        print(f"preview ok: {name}")

    created2 = req("POST", "/api/tasks/demo", {"scenario": "cancel_resume_demo"})
    run2 = created2["runId"]
    req("POST", f"/api/tasks/{run2}/start")
    time.sleep(0.5)
    cancelled = req("POST", f"/api/tasks/{run2}/cancel")
    assert cancelled["status"]["runState"] == "cancelled"
    print("cancel ok")

    replay = req("GET", f"/api/tasks/{run_id}/replay")
    assert replay.get("canResume") is not None or replay.get("can_resume") is not None
    print("replay ok")

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"API unreachable: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

# Demo Checklist

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] `GET /health` returns ok
- [ ] `POST /api/tasks/demo` with `research_success` completes with `runState: success`
- [ ] `POST /api/tasks/demo` with `quality_failure_then_revision` revises short report
- [ ] `GET /api/tasks/{id}/status` responds in < 100ms (no log read on hot path)
- [ ] `GET /api/tasks/{id}/events` shows timeline events
- [ ] SSE stream sends heartbeat every ~15s and `done` on terminal
- [ ] `GET /api/tasks/{id}/artifacts/research_report.md` returns markdown while run active
- [ ] `execution_log.jsonl` contains `research_synthesized` before `artifact_written`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

- [ ] Research Success Demo — status progress reaches 100%
- [ ] Timeline shows planner, tool, synthesis, quality, success events
- [ ] Artifact preview renders markdown
- [ ] Cancel disabled after terminal state
- [ ] Debug panel shows snapshot JSON

## E2E Script

```bash
python scripts/e2e_runtime_scenarios.py research_success
python scripts/e2e_runtime_scenarios.py quality_revision
```

## Tests

```bash
cd backend
pytest -v
```

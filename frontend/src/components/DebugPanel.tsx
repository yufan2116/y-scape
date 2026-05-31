import { auditLogUrl, replayUrl, walUrl } from "../api/client";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import type { RunEvent } from "../lib/runEvents";

interface Props {
  runId: string | null;
  status: RunStatusSnapshot | null;
  events: RunEvent[];
  error: string | null;
}

export default function DebugPanel({ runId, status, events, error }: Props) {
  if (!import.meta.env.DEV) {
    return null;
  }

  const latest = events.length > 0 ? events[events.length - 1] : null;

  return (
    <details className="glass-panel aos-glass aos-debug">
      <summary className="aos-debug-summary">
        <span>Debug</span>
        <span className="muted">snapshot · events · wal</span>
      </summary>

      <div className="aos-debug-body">
        {error && <pre className="error">{error}</pre>}

        <details>
          <summary>Latest event</summary>
          <pre>{latest ? JSON.stringify(latest, null, 2) : "—"}</pre>
        </details>

        <details>
          <summary>Raw snapshot</summary>
          <pre>{JSON.stringify(status, null, 2)}</pre>
        </details>

        {runId && (
          <div className="debug-links">
            <a href={auditLogUrl(runId)} target="_blank" rel="noreferrer">
              audit-log
            </a>
            <a href={walUrl(runId)} target="_blank" rel="noreferrer">
              wal
            </a>
            <a href={replayUrl(runId)} target="_blank" rel="noreferrer">
              replay
            </a>
          </div>
        )}

        <details>
          <summary>Recent events ({events.length})</summary>
          <pre>{JSON.stringify(events.slice(-8), null, 2)}</pre>
        </details>
      </div>
    </details>
  );
}

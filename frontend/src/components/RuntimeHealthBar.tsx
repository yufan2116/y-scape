import { auditLogUrl, replayUrl, walUrl } from "../api/client";
import { countCheckpoints } from "../lib/runtimeUtils";
import { displayText } from "../lib/display";
import type { RunEvent } from "../lib/runEvents";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import { canCancel, canResume, canRetry } from "../lib/runState";
import PanelTitle from "./PanelTitle";

interface Props {
  runId: string | null;
  status: RunStatusSnapshot | null;
  events: RunEvent[];
  sseConnected: boolean;
  usingEventPoll: boolean;
}

function fmtHeartbeat(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const sec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (sec < 5) return "刚刚";
    return `${sec}s ago`;
  } catch {
    return "—";
  }
}

export default function RuntimeHealthBar({
  runId,
  status,
  events,
  sseConnected,
  usingEventPoll,
}: Props) {
  const checkpoints = countCheckpoints(events);
  const streamLabel = sseConnected ? "LIVE" : usingEventPoll ? "POLL" : "STBY";
  const recoveryHint = status
    ? [
        canCancel(status.runState) && "Cancel",
        canRetry(status.runState) && "Retry",
        canResume(status.runState) && "Resume",
      ]
        .filter(Boolean)
        .join(" · ") || "—"
    : "—";

  return (
    <section className="glass-glow os-runtime-panel os-runtime-health">
      <PanelTitle zh="运行时健康" en="RUNTIME HEALTH" />
      <div className="os-health-grid">
        <div>
          <span className="label">Snapshot</span>
          <strong>{displayText(status?.runState, "idle")}</strong>
          {status?.isStale && <span className="badge badge-warn">stale</span>}
          {status?.syncDelayed && <span className="badge badge-warn">sync</span>}
        </div>
        <div className={sseConnected ? "ok" : usingEventPoll ? "warn" : ""}>
          <span className="label">Event Stream</span>
          <strong>
            {streamLabel} · {events.length}
          </strong>
        </div>
        <div>
          <span className="label">Checkpoint</span>
          <strong>{checkpoints > 0 ? checkpoints : "—"}</strong>
        </div>
        <div>
          <span className="label">Recovery</span>
          <strong>{recoveryHint}</strong>
        </div>
        <div>
          <span className="label">Heartbeat</span>
          <strong>{fmtHeartbeat(status?.heartbeatAt)}</strong>
        </div>
      </div>
      {import.meta.env.DEV && runId && (
        <div className="os-health-links">
          <a href={auditLogUrl(runId)} target="_blank" rel="noreferrer">
            audit
          </a>
          <a href={walUrl(runId)} target="_blank" rel="noreferrer">
            wal
          </a>
          <a href={replayUrl(runId)} target="_blank" rel="noreferrer">
            replay
          </a>
        </div>
      )}
    </section>
  );
}

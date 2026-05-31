import type { RunStatusSnapshot } from "../lib/taskTypes";
import { displayPercent, displayText } from "../lib/display";
import PanelTitle from "./PanelTitle";

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString();
  } catch {
    return "—";
  }
}

export default function StatusBar({ status }: { status: RunStatusSnapshot | null }) {
  if (!status) {
    return (
      <section className="panel sr-run-state">
        <PanelTitle zh="运行状态" en="RUN STATE" />
        <p className="muted">尚未启动任务 · Awaiting mission</p>
      </section>
    );
  }

  const pct = displayPercent(status.progress);

  return (
    <section className="panel sr-run-state">
      <PanelTitle zh="运行状态" en="RUN STATE" />
      <div className="sr-hud-grid">
        <div className="sr-hud-stat">
          <span className="label">runState</span>
          <strong className="sr-hud-value">{displayText(status.runState)}</strong>
          <span className="muted">{displayText(status.runStateLabel, "")}</span>
        </div>
        <div className="sr-hud-stat">
          <span className="label">progress</span>
          <strong className="sr-hud-value sr-hud-cyan">{pct}%</strong>
        </div>
        <div className="sr-hud-stat">
          <span className="label">currentStep</span>
          <strong className="sr-hud-value">{displayText(status.currentStep)}</strong>
        </div>
        <div className="sr-hud-stat">
          <span className="label">currentTool</span>
          <strong className="sr-hud-value">{displayText(status.currentTool)}</strong>
        </div>
        <div className="sr-hud-stat">
          <span className="label">heartbeat</span>
          <strong className="sr-hud-value sr-hud-sm">{fmtTime(status.heartbeatAt)}</strong>
        </div>
        <div className="sr-hud-stat">
          <span className="label">flags</span>
          <div>
            {status.isStale && <span className="badge badge-warn">isStale</span>}
            {status.syncDelayed && <span className="badge badge-warn">syncDelayed</span>}
            {!status.isStale && !status.syncDelayed && <span className="badge badge-success">ok</span>}
          </div>
        </div>
      </div>

      {status.thinkingMessage && (
        <p className="thinking sr-thinking-inline">{displayText(status.thinkingMessage)}</p>
      )}

      {status.error && <p className="error">{displayText(status.error)}</p>}
      {status.stopReason && <p className="warn">stopReason: {displayText(status.stopReason)}</p>}

      <div className="progress-bar sr-progress">
        <div style={{ width: `${pct}%` }} />
      </div>
    </section>
  );
}

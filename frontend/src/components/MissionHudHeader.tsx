import { displayPercent, displayText } from "../lib/display";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import type { RunEvent } from "../lib/runEvents";
import { canCancel } from "../lib/runState";
import RecoveryActions from "./RecoveryActions";

interface Props {
  runId: string | null;
  status: RunStatusSnapshot | null;
  events: RunEvent[];
  recoveryLoading: boolean;
  onCancel: () => void;
  onRetry: () => void;
  onResume: () => void;
  onStartNew: () => void;
}

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return "—";
  }
}

function stateBadgeClass(runState?: string): string {
  if (!runState) return "";
  if (["success", "degraded_success"].includes(runState)) return "ref-status-success";
  if (["failed", "cancelled", "timeout"].includes(runState)) return "ref-status-failed";
  return "ref-status-running";
}

export default function MissionHudHeader({
  runId,
  status,
  events,
  recoveryLoading,
  onCancel,
  onRetry,
  onResume,
  onStartNew,
}: Props) {
  const metrics = estimateDemoMetrics(status, events);
  const pct = displayPercent(status?.progress);
  const toolSteps = events.filter((e) => e.type === "tool_succeeded").length;
  const maxSteps = 20;
  const showPause = status && canCancel(status.runState);

  return (
    <header className="ref-mission-header glass-panel aos-mission-header aos-glass">
      <div className="ref-mission-top">
        <div>
          <span className="ref-mission-label">TASK HEADER</span>
          <h2 className="ref-mission-id">
            {runId ? `#${displayText(runId.slice(-8))}` : "# —"}
          </h2>
          <div className="ref-mission-meta">
            <span>创建 · {fmtTime(status?.startedAt)}</span>
            <span>更新 · {fmtTime(status?.updatedAt)}</span>
          </div>
        </div>

        {status && (
          <span className={`ref-status-pill ${stateBadgeClass(status.runState)}`}>
            {displayText(status.runStateLabel || status.runState, "待机")}
          </span>
        )}

        <div className="aos-header-actions">
          {showPause && (
            <button type="button" className="ref-btn aos-btn-pause" disabled title="暂停功能即将上线">
              ⏸ 暂停任务
            </button>
          )}
          <RecoveryActions
            status={status}
            loading={recoveryLoading}
            onCancel={onCancel}
            onRetry={onRetry}
            onResume={onResume}
            onStartNew={onStartNew}
          />
        </div>
      </div>

      <div className="ref-hud-metrics">
        <div className="ref-metric aos-metric-bar">
          <span className="ref-metric-icon ref-icon-progress" aria-hidden />
          <div>
            <span className="label">进度 · Progress</span>
            <strong>{pct}%</strong>
            <div className="progress-bar ref-metric-bar">
              <div style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>
        <div className="ref-metric">
          <span className="ref-metric-icon ref-icon-steps" aria-hidden />
          <div>
            <span className="label">步骤 · Steps</span>
            <strong>
              {toolSteps} / {maxSteps}
            </strong>
          </div>
        </div>
        <div className="ref-metric">
          <span className="ref-metric-icon ref-icon-tokens" aria-hidden />
          <div>
            <span className="label">Tokens</span>
            <strong>{metrics.tokens.toLocaleString()}</strong>
          </div>
        </div>
        <div className="ref-metric">
          <span className="ref-metric-icon ref-icon-cost" aria-hidden />
          <div>
            <span className="label">消耗 · Cost</span>
            <strong>${metrics.cost.toFixed(4)}</strong>
          </div>
        </div>
      </div>
    </header>
  );
}

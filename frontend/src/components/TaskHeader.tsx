import { displayPercent, displayText } from "../lib/display";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import type { RunEvent } from "../lib/runEvents";
import {
  canCancel,
  canResume,
  canRetry,
  canStartNewMission,
} from "../lib/runState";

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

function fmtDateTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "—";
  }
}

function fmtUpdateTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "—";
  }
}

function badgeClass(runState?: string): string {
  if (!runState) return "th-badge-idle";
  if (["success", "degraded_success"].includes(runState)) return "th-badge-success";
  if (["failed", "cancelled", "timeout"].includes(runState)) return "th-badge-failed";
  return "th-badge-running";
}

function badgeLabel(status: RunStatusSnapshot | null): string {
  if (!status) return "待机";
  const label = displayText(status.runStateLabel, "");
  if (label && label !== "—") return label;
  const map: Record<string, string> = {
    success: "已完成",
    degraded_success: "已完成",
    failed: "失败",
    cancelled: "已取消",
    timeout: "超时",
    idle: "待机",
  };
  return map[status.runState] ?? "运行中";
}

export default function TaskHeader({
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
  const showCancel = status && canCancel(status.runState);
  const showRetry = status && canRetry(status.runState);
  const showResume = status && canResume(status.runState);
  const showStartNew = status && canStartNewMission(status.runState);

  const isRunning =
    status &&
    !["success", "degraded_success", "failed", "cancelled", "timeout", "idle"].includes(
      status.runState,
    );

  return (
    <header className="th-bar">
      <span className="th-hud-corner th-hud-tl" aria-hidden />
      <span className="th-hud-corner th-hud-tr" aria-hidden />

      <div className="th-identity">
        <div className="th-title-row">
          <h1 className="th-task-id">
            任务：{runId ? `#${displayText(runId.slice(-8))}` : "# —"}
          </h1>
          {status && (
            <span className={`th-badge ${badgeClass(status.runState)}`}>
              {badgeLabel(status)}
            </span>
          )}
        </div>
        <div className="th-times">
          <span>创建时间: {fmtDateTime(status?.startedAt)}</span>
          <span>更新时间: {fmtUpdateTime(status?.updatedAt)}</span>
        </div>
      </div>

      <div className="th-right">
        <div className="th-metrics">
          <div className={`th-chip th-chip-progress metric-card${isRunning ? " is-running" : ""}`}>
            <span className="th-chip-icon th-icon-progress" aria-hidden />
            <div className="th-chip-body">
              <span className="th-chip-label">进度</span>
              <div className="th-chip-value-row">
                <div className="th-progress-track">
                  <div className="th-progress-fill" style={{ width: `${pct}%` }} />
                </div>
                <strong className="metric-value">{pct}%</strong>
              </div>
            </div>
          </div>

          <div className="th-chip metric-card">
            <span className="th-chip-icon th-icon-steps" aria-hidden />
            <div className="th-chip-body">
              <span className="th-chip-label">步骤</span>
              <strong className="th-chip-value metric-value">
                {toolSteps} / {maxSteps}
              </strong>
            </div>
          </div>

          <div className="th-chip metric-card">
            <span className="th-chip-icon th-icon-tokens" aria-hidden />
            <div className="th-chip-body">
              <span className="th-chip-label">Tokens</span>
              <strong className="th-chip-value metric-value">{metrics.tokens.toLocaleString()}</strong>
            </div>
          </div>

          <div className="th-chip metric-card">
            <span className="th-chip-icon th-icon-cost" aria-hidden />
            <div className="th-chip-body">
              <span className="th-chip-label">消耗</span>
              <strong className="th-chip-value metric-value">${metrics.cost.toFixed(4)}</strong>
            </div>
          </div>
        </div>

        <div className="th-actions">
          {showPause && (
            <button
              type="button"
              className="th-btn th-btn-pause hud-button"
              disabled
              title="暂停功能即将上线"
            >
              <span className="th-btn-icon" aria-hidden>
                ⏸
              </span>
              暂停任务
            </button>
          )}
          {showCancel && (
            <button
              type="button"
              className="th-btn th-btn-cancel hud-button"
              disabled={recoveryLoading}
              onClick={onCancel}
            >
              <span className="th-btn-icon" aria-hidden>
                ✕
              </span>
              终止任务
            </button>
          )}
          {showRetry && (
            <button
              type="button"
              className="th-btn th-btn-ghost hud-button"
              disabled={recoveryLoading}
              onClick={onRetry}
            >
              ↻ Retry
            </button>
          )}
          {showResume && (
            <button
              type="button"
              className="th-btn th-btn-ghost hud-button"
              disabled={recoveryLoading}
              onClick={onResume}
            >
              ▶ Resume
            </button>
          )}
          {showStartNew && (
            <button
              type="button"
              className="th-btn th-btn-ghost hud-button"
              disabled={recoveryLoading}
              onClick={onStartNew}
            >
              ＋ New
            </button>
          )}
        </div>

        <div className="th-util" aria-hidden>
          <span className="th-util-icon th-util-star">✦</span>
          <span className="th-util-icon th-util-bell">🔔</span>
          <span className="th-util-icon th-util-avatar" />
        </div>
      </div>
    </header>
  );
}

import { displayPercent, displayText } from "../lib/display";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import type { RunEvent } from "../lib/runEvents";
import MissionComposer from "./MissionComposer";
import RecoveryActions from "./RecoveryActions";

interface Props {
  runId: string | null;
  status: RunStatusSnapshot | null;
  events: RunEvent[];
  starting: boolean;
  restoring: boolean;
  recoveryLoading: boolean;
  error: string | null;
  onStart: (scenario: string, goal?: string) => void;
  onCancel: () => void;
  onRetry: () => void;
  onResume: () => void;
  onStartNew: () => void;
}

export default function MissionBar({
  runId,
  status,
  events,
  starting,
  restoring,
  recoveryLoading,
  error,
  onStart,
  onCancel,
  onRetry,
  onResume,
  onStartNew,
}: Props) {
  const metrics = estimateDemoMetrics(status, events);
  const pct = displayPercent(status?.progress);

  return (
    <header className="glass-glow pf-mission">
      <div className="pf-mission-primary">
        <div className="pf-brand">
          <span className="pf-brand-mark" aria-hidden />
          <div>
            <strong>Y-Space</strong>
            <span>Agent OS</span>
          </div>
        </div>

        <div className="pf-mission-body">
          <span className="pf-kicker">Mission</span>
          <h1 className="pf-mission-goal">{displayText(status?.goal, "选择场景并启动 Agent Mission")}</h1>
          <div className="pf-mission-meta">
            {runId && <code>{displayText(runId)}</code>}
            <span>{pct}%</span>
            <span>{metrics.tokens.toLocaleString()} tok</span>
          </div>
        </div>

        {status && (
          <span className={`pf-state-badge pf-state-${status.runState}`}>
            {displayText(status.runStateLabel || status.runState)}
          </span>
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

      <MissionComposer
        variant="compact"
        runId={runId}
        onStart={onStart}
        starting={starting}
        restoring={restoring}
        error={error}
      />
    </header>
  );
}

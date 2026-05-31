import type { RunStatusSnapshot } from "../lib/taskTypes";
import { canCancel, canResume, canRetry, canStartNewMission } from "../lib/runState";

interface Props {
  status: RunStatusSnapshot | null;
  loading: boolean;
  onCancel: () => void;
  onRetry: () => void;
  onResume: () => void;
  onStartNew: () => void;
}

export default function RecoveryActions({
  status,
  loading,
  onCancel,
  onRetry,
  onResume,
  onStartNew,
}: Props) {
  if (!status) return null;

  const showCancel = canCancel(status.runState);
  const showRetry = canRetry(status.runState);
  const showResume = canResume(status.runState);
  const showStartNew = canStartNewMission(status.runState);

  if (!showCancel && !showRetry && !showResume && !showStartNew) {
    return null;
  }

  return (
    <div className="ref-recovery-actions pf-recovery">
      {showStartNew && (
        <button type="button" className="ref-btn ref-btn-primary" disabled={loading} onClick={onStartNew}>
          ＋ New Mission
        </button>
      )}
      {showCancel && (
        <button type="button" className="ref-btn ref-btn-danger" disabled={loading} onClick={onCancel}>
          ✕ 终止任务
        </button>
      )}
      {showRetry && (
        <button type="button" className="ref-btn ref-btn-ghost" disabled={loading} onClick={onRetry}>
          ↻ Retry
        </button>
      )}
      {showResume && (
        <button type="button" className="ref-btn ref-btn-outline" disabled={loading} onClick={onResume}>
          ▶ Resume
        </button>
      )}
    </div>
  );
}

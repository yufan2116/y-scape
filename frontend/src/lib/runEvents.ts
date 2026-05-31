export type RunEventType =
  | "run_started"
  | "planner_started"
  | "planner_response"
  | "tool_started"
  | "tool_succeeded"
  | "tool_failed"
  | "artifact_written"
  | "quality_check_started"
  | "quality_check_failed"
  | "quality_check_passed"
  | "quality_revision_started"
  | "research_synthesized"
  | "finalizing"
  | "run_succeeded"
  | "run_degraded_success"
  | "run_failed"
  | "run_cancelled"
  | "run_timeout"
  | "state_changed"
  | "checkpoint_saved"
  | "wal_replay_started"
  | "wal_replay_completed"
  | "checkpoint_restored";

export interface RunEvent {
  eventId: string;
  runId: string;
  timestamp: string;
  type: RunEventType;
  runState: string;
  label: string;
  message: string;
  description?: string;
  iteration?: number;
  tool?: string | null;
  payload?: Record<string, unknown>;
}

/** Timeline highlights — tool / quality / artifact / terminal */
export const TIMELINE_HIGHLIGHT_TYPES: Set<RunEventType> = new Set([
  "tool_started",
  "tool_succeeded",
  "tool_failed",
  "quality_check_started",
  "quality_check_failed",
  "quality_check_passed",
  "quality_revision_started",
  "artifact_written",
  "research_synthesized",
  "run_succeeded",
  "run_failed",
  "run_cancelled",
  "run_timeout",
  "finalizing",
]);

export const ALL_SSE_EVENT_TYPES: RunEventType[] = [
  "run_started",
  "planner_started",
  "planner_response",
  "tool_started",
  "tool_succeeded",
  "tool_failed",
  "artifact_written",
  "quality_check_started",
  "quality_check_failed",
  "quality_check_passed",
  "quality_revision_started",
  "research_synthesized",
  "finalizing",
  "run_succeeded",
  "run_degraded_success",
  "run_failed",
  "run_cancelled",
  "run_timeout",
  "state_changed",
  "checkpoint_saved",
  "wal_replay_started",
  "wal_replay_completed",
  "checkpoint_restored",
];

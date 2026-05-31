export type RunState =
  | "created"
  | "planning"
  | "thinking"
  | "tool_pending"
  | "tool_running"
  | "tool_success"
  | "tool_failed"
  | "synthesizing_research"
  | "writing_artifact"
  | "quality_revision"
  | "quality_blocked"
  | "finalizing"
  | "success"
  | "degraded_success"
  | "failed"
  | "cancelled"
  | "timeout"
  | "needs_input"
  | "stale"
  | "recovering"
  | "retrying"
  | "interrupted";

export const TERMINAL_STATES: RunState[] = [
  "success",
  "degraded_success",
  "failed",
  "cancelled",
  "timeout",
  "needs_input",
  "stale",
  "interrupted",
  "quality_blocked",
];

export function isTerminal(state: RunState): boolean {
  return TERMINAL_STATES.includes(state);
}

export function canCancel(state: RunState): boolean {
  return !isTerminal(state);
}

export function canResume(state: RunState): boolean {
  return ["interrupted", "stale", "tool_failed"].includes(state);
}

export function canRetry(state: RunState): boolean {
  return ["failed", "timeout", "quality_blocked"].includes(state);
}

export function canStartNewMission(state: RunState | null | undefined): boolean {
  if (!state) return false;
  return state === "success" || state === "degraded_success";
}

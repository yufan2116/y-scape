import type { RunEvent } from "./runEvents";
import type { RunStatusSnapshot } from "./taskTypes";

/** Demo-only estimates — no backend token API */
export function estimateDemoMetrics(status: RunStatusSnapshot | null, events: RunEvent[]) {
  if (!status) {
    return { tokens: 0, cost: 0, label: "—" };
  }
  const iter = status.iteration ?? 1;
  const toolRuns = events.filter((e) => e.type === "tool_succeeded").length;
  const tokens = Math.max(1200, events.length * 620 + toolRuns * 2400 + iter * 800);
  const cost = tokens * 0.0000018;
  return {
    tokens,
    cost,
    label: status.demoMode === false ? "Est." : "Demo est.",
  };
}

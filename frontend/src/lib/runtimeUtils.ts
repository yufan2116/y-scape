import type { RunEvent } from "./runEvents";

export function countCheckpoints(events: RunEvent[]): number {
  return events.filter((e) => e.type === "checkpoint_saved" || e.type === "checkpoint_restored").length;
}

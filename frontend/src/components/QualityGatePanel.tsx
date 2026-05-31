import type { RunEvent } from "../lib/runEvents";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import { displayText } from "../lib/display";
import PanelTitle from "./PanelTitle";

interface Props {
  status: RunStatusSnapshot | null;
  events: RunEvent[];
}

function qualityState(status: RunStatusSnapshot | null, events: RunEvent[]) {
  const types = new Set(events.map((e) => e.type));
  if (status?.runState === "quality_blocked") return { label: "Blocked", tone: "danger" as const };
  if (types.has("quality_check_failed")) {
    if (types.has("quality_check_passed")) return { label: "Revised", tone: "warn" as const };
    return { label: "Failed", tone: "danger" as const };
  }
  if (types.has("quality_check_passed")) return { label: "Passed", tone: "success" as const };
  if (types.has("quality_check_started") || status?.runState === "quality_revision") {
    return { label: "Checking", tone: "running" as const };
  }
  return { label: "Pending", tone: "muted" as const };
}

export default function QualityGatePanel({ status, events }: Props) {
  const q = qualityState(status, events);
  const revision = status?.revisionAttempt ?? 0;
  const lastQuality = [...events]
    .reverse()
    .find((e) => e.type.startsWith("quality_check") || e.type === "quality_revision_started");

  return (
    <section className="glass-glow os-runtime-panel os-quality">
      <PanelTitle zh="质量门控" en="QUALITY GATE" />
      <div className={`os-quality-badge os-quality-${q.tone}`}>{q.label}</div>
      <dl className="os-quality-stats">
        <div>
          <dt>Revision</dt>
          <dd>{revision}</dd>
        </div>
        <div>
          <dt>Last check</dt>
          <dd>{displayText(lastQuality?.type, "—")}</dd>
        </div>
      </dl>
      {lastQuality && <p className="muted os-quality-msg">{displayText(lastQuality.message)}</p>}
    </section>
  );
}

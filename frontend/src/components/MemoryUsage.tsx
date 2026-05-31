import type { RunEvent } from "../lib/runEvents";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import { displayText } from "../lib/display";
import PanelTitle from "./PanelTitle";

interface Props {
  status: RunStatusSnapshot | null;
  events: RunEvent[];
}

export default function MemoryUsage({ status, events }: Props) {
  const metrics = estimateDemoMetrics(status, events);
  const iter = status?.iteration ?? 0;
  const cap = 128_000;
  const usedPct = Math.min(100, Math.round((metrics.tokens / cap) * 100));

  return (
    <section className="glass-glow os-runtime-panel os-memory">
      <PanelTitle zh="记忆占用" en="MEMORY USAGE" />
      <div className="os-memory-bar-wrap">
        <div className="os-memory-bar ref-memory-segments">
          <div className="os-memory-fill" style={{ width: `${usedPct}%` }} />
        </div>
        <span className="os-memory-pct">{usedPct}%</span>
      </div>
      <dl className="os-memory-stats">
        <div>
          <dt>Context</dt>
          <dd>{metrics.tokens.toLocaleString()} tok</dd>
        </div>
        <div>
          <dt>Iteration</dt>
          <dd>{displayText(iter, "0")}</dd>
        </div>
        <div>
          <dt>Events</dt>
          <dd>{events.length}</dd>
        </div>
      </dl>
    </section>
  );
}

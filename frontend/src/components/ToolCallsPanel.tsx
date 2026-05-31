import type { RunEvent } from "../lib/runEvents";
import { displayText } from "../lib/display";
import PanelTitle from "./PanelTitle";

interface Props {
  events: RunEvent[];
  currentTool: string | null | undefined;
}

export default function ToolCallsPanel({ events, currentTool }: Props) {
  const toolEvents = events.filter((e) =>
    ["tool_started", "tool_succeeded", "tool_failed"].includes(e.type),
  );
  const recent = toolEvents.slice(-6);
  const activeTool = displayText(currentTool, "");

  return (
    <section className="panel sr-tools-panel glass-panel">
      <PanelTitle zh="工具调用" en="TOOL CALLS" />
      {activeTool && activeTool !== "—" && (
        <div className="sr-tool-active">
          <span className="sr-tool-pulse" aria-hidden />
          <span className="sr-truncate">{activeTool}</span>
          <span className="badge badge-running">Running</span>
        </div>
      )}
      <ul className="sr-tool-list">
        {recent.length === 0 && <li className="muted">暂无工具调用记录 · No tool calls</li>}
        {recent.map((ev) => (
          <li key={ev.eventId} className={`sr-tool-item sr-tool-${ev.type}`}>
            <span className="sr-tool-name sr-truncate">{displayText(ev.tool ?? ev.label)}</span>
            <span
              className={`badge badge-${ev.type === "tool_succeeded" ? "success" : ev.type === "tool_failed" ? "danger" : "running"}`}
            >
              {ev.type === "tool_started" ? "Running" : ev.type === "tool_succeeded" ? "Success" : "Failed"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

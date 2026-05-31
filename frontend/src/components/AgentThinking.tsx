import { displayText } from "../lib/display";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import type { RunEvent } from "../lib/runEvents";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import PanelTitle from "./PanelTitle";
import "../styles/thinkingPanel.css";

interface Props {
  message?: string | null;
  latestReasoning?: string | null;
  currentStep?: string | null;
  events: RunEvent[];
  currentTool?: string | null;
  status: RunStatusSnapshot | null;
}

function extractFindings(source: string): string[] {
  if (!source || source === "—") return [];

  const numbered = source.match(/^\s*\d+[.)]\s*.+/gm);
  if (numbered && numbered.length >= 2) {
    return numbered
      .map((line) => line.replace(/^\s*\d+[.)]\s*/, "").trim())
      .filter((s) => s.length > 4)
      .slice(0, 4);
  }

  const lines = source
    .split(/[\n•\-*]/)
    .map((s) => s.replace(/^\s*\d+[.)]\s*/, "").trim())
    .filter((s) => s.length > 8);

  if (lines.length >= 2) return lines.slice(0, 4);

  const sentences = source
    .split(/[。；;!?！？]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 6);

  return sentences.slice(0, 4);
}

function buildToolQueue(
  events: RunEvent[],
  currentTool: string,
): { name: string; status: "running" | "waiting" | "done" }[] {
  const seen = new Set<string>();
  const queue: { name: string; status: "running" | "waiting" | "done" }[] = [];

  for (const ev of events) {
    if (!["tool_started", "tool_succeeded", "tool_failed"].includes(ev.type)) continue;
    const name = ev.tool ?? ev.label;
    if (!name || seen.has(name)) continue;
    seen.add(name);
    queue.push({
      name,
      status:
        ev.type === "tool_succeeded" || ev.type === "tool_failed"
          ? "done"
          : name === currentTool
            ? "running"
            : "waiting",
    });
  }

  if (currentTool && currentTool !== "—" && !seen.has(currentTool)) {
    queue.push({ name: currentTool, status: "running" });
  }

  return queue.slice(-6);
}

export default function AgentThinking({
  message,
  latestReasoning,
  currentStep,
  events,
  currentTool,
  status,
}: Props) {
  const reasoning = displayText(latestReasoning, "");
  const thinking = displayText(message, "");
  const next = displayText(currentStep, "");
  const activeTool = displayText(currentTool, "");
  const metrics = estimateDemoMetrics(status, events);
  const thoughtNum =
    events.filter((e) => e.type === "planner_response" || e.type === "state_changed").length + 1;

  const bodyText = reasoning || thinking;
  const findingsSource = reasoning || thinking;
  const findings = extractFindings(findingsSource);
  const toolQueue = buildToolQueue(events, activeTool);
  const cap = 128_000;
  const usedPct = Math.min(100, Math.round((metrics.tokens / cap) * 100));

  return (
    <div className="aos-agent-col">
      <section className="thinking-card">
        <header className="thinking-card__header">
          <PanelTitle zh="思考过程" en="AGENT THINKING" />
          <span className="thinking-card__tokens">Tokens: {metrics.tokens.toLocaleString()}</span>
        </header>

        <div className="thinking-card__body">
          <div className="thinking-card__current">
            <h3 className="thinking-card__thought-num">Thought #{thoughtNum}</h3>
            {bodyText ? (
              <p className="thinking-card__content">{bodyText}</p>
            ) : (
              <p className="thinking-card__placeholder">Agent 思维流将在此实时呈现…</p>
            )}
          </div>

          {findings.length > 0 && (
            <section className="thinking-card__findings">
              <h4 className="thinking-card__section-label">关键发现</h4>
              <ol className="thinking-card__findings-list">
                {findings.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ol>
            </section>
          )}

          {next && next !== "—" && (
            <section className="thinking-card__next">
              <h4 className="thinking-card__section-label">接下来</h4>
              <p className="thinking-card__next-text">{next}</p>
            </section>
          )}
        </div>
      </section>

      <section className="glass-panel aos-tools-panel aos-glass">
        <PanelTitle zh="工具调用" en="TOOL CALLS" />

        <ul className="aos-tool-queue">
          {toolQueue.length === 0 && (
            <li className="aos-tool-waiting muted">暂无工具调用 · No tool calls</li>
          )}
          {toolQueue.map((tool) => (
            <li
              key={tool.name}
              className={
                tool.status === "running"
                  ? "aos-tool-running"
                  : tool.status === "waiting"
                    ? "aos-tool-waiting"
                    : ""
              }
            >
              <span className="sr-tool-name">{tool.name}</span>
              <span className="aos-tool-status">
                <span
                  className={`badge badge-${tool.status === "done" ? "success" : tool.status === "running" ? "running" : "warn"}`}
                >
                  {tool.status === "running" ? "运行中" : tool.status === "done" ? "完成" : "等待中"}
                </span>
                <span className="aos-tool-arrow">→</span>
              </span>
            </li>
          ))}
        </ul>

        <div className="aos-memory-inline">
          <span className="label">Memory Usage · Token 占用</span>
          <div className="aos-memory-segments">
            <div className="aos-memory-fill" style={{ width: `${usedPct}%` }} />
          </div>
          <div className="aos-memory-row">
            <span>
              {metrics.tokens.toLocaleString()} / {cap.toLocaleString()} tok
            </span>
            <span>{usedPct}%</span>
          </div>
        </div>
      </section>
    </div>
  );
}

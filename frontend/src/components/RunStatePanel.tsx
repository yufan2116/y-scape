import type { RunStatusSnapshot } from "../lib/taskTypes";
import { displayText } from "../lib/display";
import OrbitPlanet from "./OrbitPlanet";

interface Props {
  status: RunStatusSnapshot | null;
}

function stateEnLabel(runState?: string, currentStep?: string | null): string {
  if (currentStep) {
    const lower = currentStep.toLowerCase();
    if (lower.includes("synth") || lower.includes("综合")) return "Synthesizing Research";
    if (lower.includes("search") || lower.includes("搜索")) return "Web Search";
    if (lower.includes("write") || lower.includes("报告")) return "Writing Report";
    if (lower.includes("plan") || lower.includes("计划")) return "Planning Mission";
  }
  const map: Record<string, string> = {
    thinking: "Agent Thinking",
    tool_running: "Tool Execution",
    synthesizing_research: "Synthesizing Research",
    success: "Mission Complete",
    failed: "Mission Failed",
    idle: "Standby",
  };
  return map[runState ?? ""] ?? displayText(runState, "Standby");
}

export default function RunStatePanel({ status }: Props) {
  const stateLabel = displayText(
    status?.thinkingMessage || status?.runStateLabel || status?.currentStep,
    "等待 Agent 启动…",
  );
  const stateEn = stateEnLabel(status?.runState, status?.currentStep);

  return (
    <section className="hud-panel hud-panel--state">
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />

      <header className="hud-panel__head">
        <span className="hud-panel__diamond" aria-hidden />
        <div className="hud-panel__titles">
          <h3 className="hud-panel__title">当前状态</h3>
          <span className="hud-panel__subtitle">RUN STATE</span>
        </div>
      </header>

      <div className="hud-panel__body hud-panel__body--state">
        <div className="hud-panel__state-text">
          <p className="hud-panel__state-primary">{stateLabel}</p>
          <p className="hud-panel__state-secondary">{stateEn}</p>
        </div>
        <div className="hud-panel__state-visual">
          <OrbitPlanet />
        </div>
      </div>
    </section>
  );
}

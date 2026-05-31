import type { RunEvent } from "../lib/runEvents";
import type { RunState } from "../lib/runState";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import { estimateDemoMetrics } from "../lib/demoMetrics";
import { NAV_ITEMS, type ActiveView } from "../lib/viewNav";
import AgentProfileCard, { type AgentHealth } from "./AgentProfileCard";

interface Props {
  runId: string | null;
  status: RunStatusSnapshot | null;
  events: RunEvent[];
  activeView: ActiveView;
  onNavigate: (view: ActiveView) => void;
}

function deriveHealth(status: RunStatusSnapshot | null): AgentHealth {
  if (!status) return "stable";
  if (status.error || status.runState === "failed" || status.runState === "cancelled") {
    return "error";
  }
  if (status.isStale || status.syncDelayed) return "warning";
  return "stable";
}

function deriveModelName(status: RunStatusSnapshot | null): string {
  if (!status) return "Demo";
  if (status.demoMode === false) return "Gemini";
  return "Demo";
}

function deriveQuote(status: RunStatusSnapshot | null): string {
  if (!status?.runId) return "Research core online.";
  if (isActiveRunState(status.runState)) return "Research core online.";
  if (status.runState === "success" || status.runState === "degraded_success") {
    return "Research core online.";
  }
  if (status.runState === "failed" || status.runState === "timeout") {
    return "Core interrupted.";
  }
  return "Research core online.";
}

function isActiveRunState(state: RunState): boolean {
  return [
    "planning",
    "thinking",
    "tool_pending",
    "tool_running",
    "tool_success",
    "synthesizing_research",
    "writing_artifact",
    "quality_revision",
    "finalizing",
    "recovering",
    "retrying",
  ].includes(state);
}

export default function Sidebar({ status, events, activeView, onNavigate }: Props) {
  const metrics = estimateDemoMetrics(status, events);
  const contextLimit = 20480;
  const contextUsed = Math.min(contextLimit, metrics.tokens);
  const memoryPercent =
    status?.progress != null && status.progress > 0
      ? Math.min(100, Math.round(status.progress))
      : Math.min(100, Math.max(12, Math.round((contextUsed / contextLimit) * 100)));

  const handleNav = (view: ActiveView) => {
    onNavigate(view);
  };

  return (
    <aside className="ref-sidebar glass-panel aos-sidebar">
      <div className="ref-sidebar-logo">
        <div className="sr-logo-mark aos-avatar-orbit" aria-hidden />
        <div>
          <strong>Y-Space</strong>
          <span>AI Sandbox OS</span>
        </div>
      </div>

      <nav className="ref-nav" aria-label="主导航">
        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.view;
          return (
            <button
              key={item.view}
              type="button"
              className={`ref-nav-item ref-nav-btn${isActive ? " active" : ""}`}
              aria-current={isActive ? "page" : undefined}
              onClick={() => handleNav(item.view)}
            >
              <span className="ref-nav-icon" aria-hidden>
                {item.icon}
              </span>
              <span className="ref-nav-zh">{item.zh}</span>
              <span className="ref-nav-en">{item.en}</span>
            </button>
          );
        })}
      </nav>

      <AgentProfileCard
        agentName="Y-Space Agent"
        agentType="RESEARCH AGENT"
        modelName={deriveModelName(status)}
        memoryPercent={memoryPercent}
        health={deriveHealth(status)}
        saveEnabled
        quote={deriveQuote(status)}
      />
    </aside>
  );
}

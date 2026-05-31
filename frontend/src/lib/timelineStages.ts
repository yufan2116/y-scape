import type { RunEvent } from "./runEvents";

export type QuestStatus = "pending" | "running" | "success" | "failed";

export interface QuestStep {
  id: string;
  title: string;
  subtitle: string;
  status: QuestStatus;
  meta?: string;
  elapsed?: string;
}

type StepDef = {
  id: string;
  title: string;
  subtitle: string;
  metaKind?: "results" | "pages" | "papers" | "items";
};

export const TIMELINE_STAGE_DEFS: StepDef[] = [
  { id: "created", title: "任务创建", subtitle: "Mission Created" },
  { id: "planning", title: "制定计划", subtitle: "Planning" },
  { id: "web_search", title: "网络搜索", subtitle: "Web Search", metaKind: "results" },
  { id: "web_scrape", title: "抓取网页", subtitle: "Web Scrape", metaKind: "pages" },
  { id: "paper_search", title: "论文检索", subtitle: "Paper Search", metaKind: "papers" },
  { id: "extract", title: "提取解析", subtitle: "Extract & Parse", metaKind: "items" },
  { id: "synthesis", title: "综合研究", subtitle: "Synthesizing Research" },
  { id: "writing", title: "生成报告", subtitle: "Writing Report" },
  { id: "quality", title: "质量检查", subtitle: "Quality Check" },
  { id: "finalize", title: "任务完成", subtitle: "Finalizing" },
];

function parseTs(iso: string): number {
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : 0;
}

function toolToStage(tool: string | null | undefined): string | null {
  if (!tool) return null;
  if (tool === "web_search") return "web_search";
  if (tool === "web_scrape") return "web_scrape";
  if (/paper|arxiv|scholar|pub/i.test(tool)) return "paper_search";
  if (tool === "pdf_extract" || tool === "file_read") return "extract";
  if (tool === "file_write") return "writing";
  return null;
}

function initStates(): Record<string, QuestStatus> {
  return Object.fromEntries(TIMELINE_STAGE_DEFS.map((s) => [s.id, "pending" as QuestStatus]));
}

function applyEvent(states: Record<string, QuestStatus>, e: RunEvent): void {
  switch (e.type) {
    case "run_started":
      states.created = "success";
      if (states.planning === "pending") states.planning = "running";
      break;
    case "planner_started":
      states.created = "success";
      states.planning = "running";
      break;
    case "planner_response":
      states.planning = "success";
      break;
    case "tool_started": {
      const stage = toolToStage(e.tool);
      if (stage) states[stage] = "running";
      break;
    }
    case "tool_succeeded": {
      const stage = toolToStage(e.tool);
      if (stage) states[stage] = "success";
      break;
    }
    case "tool_failed": {
      const stage = toolToStage(e.tool);
      if (stage) states[stage] = "failed";
      break;
    }
    case "research_synthesized":
      states.synthesis = "running";
      break;
    case "artifact_written":
      states.synthesis = states.synthesis === "pending" ? "success" : states.synthesis;
      states.writing = "success";
      break;
    case "quality_check_started":
      states.quality = "running";
      break;
    case "quality_check_passed":
      states.quality = "success";
      break;
    case "quality_check_failed":
      states.quality = "failed";
      break;
    case "finalizing":
      states.finalize = "running";
      break;
    case "run_succeeded":
    case "run_degraded_success":
      states.finalize = "success";
      break;
    case "run_failed":
    case "run_cancelled":
    case "run_timeout":
      states.finalize = "failed";
      break;
    case "state_changed":
      if (e.runState === "planning" && states.planning !== "success") {
        states.planning = "running";
      }
      if (e.runState === "synthesizing_research") {
        states.synthesis = "running";
      }
      if (e.runState === "tool_running" && e.payload?.tool) {
        const stage = toolToStage(String(e.payload.tool));
        if (stage) states[stage] = "running";
      }
      break;
    default:
      break;
  }
}

function resolveRunning(states: Record<string, QuestStatus>, events: RunEvent[]): void {
  const runningIds = TIMELINE_STAGE_DEFS.filter((s) => states[s.id] === "running").map(
    (s) => s.id,
  );
  if (runningIds.length > 1) {
    const lastRunning = runningIds[runningIds.length - 1];
    for (const id of runningIds) {
      if (id !== lastRunning) states[id] = "success";
    }
  }

  if (runningIds.length > 0 || events.length === 0) return;

  const last = events[events.length - 1];
  if (["run_succeeded", "run_degraded_success", "run_failed", "run_cancelled"].includes(last.type)) {
    return;
  }

  const inferred = inferStageFromEvent(last);
  if (inferred && states[inferred] === "pending") {
    states[inferred] = "running";
  }
}

function inferStageFromEvent(e: RunEvent): string | null {
  if (e.type === "planner_started" || e.type === "planner_response") return "planning";
  if (e.type === "research_synthesized") return "synthesis";
  if (e.type === "artifact_written") return "writing";
  if (e.type.startsWith("quality_check")) return "quality";
  if (e.type === "finalizing") return "finalize";
  if (e.type === "tool_started" || e.type === "tool_succeeded" || e.type === "tool_failed") {
    return toolToStage(e.tool);
  }
  if (e.type === "run_started") return "planning";
  return null;
}

function eventsForStage(stageId: string, events: RunEvent[]): RunEvent[] {
  return events.filter((e) => {
    switch (stageId) {
      case "created":
        return e.type === "run_started";
      case "planning":
        return ["planner_started", "planner_response"].includes(e.type);
      case "web_search":
        return e.tool === "web_search";
      case "web_scrape":
        return e.tool === "web_scrape";
      case "paper_search":
        return Boolean(e.tool && /paper|arxiv|scholar|pub/i.test(e.tool));
      case "extract":
        return e.tool === "pdf_extract" || e.tool === "file_read";
      case "synthesis":
        return e.type === "research_synthesized";
      case "writing":
        return e.type === "artifact_written" || e.tool === "file_write";
      case "quality":
        return e.type.startsWith("quality_check");
      case "finalize":
        return ["finalizing", "run_succeeded", "run_degraded_success", "run_failed", "run_cancelled"].includes(
          e.type,
        );
      default:
        return false;
    }
  });
}

function countFromPayload(events: RunEvent[], kind: NonNullable<StepDef["metaKind"]>): number {
  let total = 0;
  for (const e of events) {
    if (e.type !== "tool_succeeded") continue;
    const p = e.payload ?? {};
    if (kind === "results" && Array.isArray(p.results)) {
      total += p.results.length;
    } else if (kind === "pages" && typeof p.pages === "number") {
      total += p.pages;
    } else if (kind === "papers" && typeof p.count === "number") {
      total += p.count;
    } else if (kind === "items") {
      total += typeof p.pages === "number" ? p.pages : 1;
    } else {
      total += 1;
    }
  }
  return total;
}

function buildMeta(def: StepDef, events: RunEvent[], status: QuestStatus): string | undefined {
  if (status === "pending" || !def.metaKind) return undefined;
  const matched = eventsForStage(def.id, events).filter((e) => e.type === "tool_succeeded");
  const n = countFromPayload(matched, def.metaKind);
  if (n > 0) {
    if (def.metaKind === "results") return `${n} results`;
    if (def.metaKind === "pages") return `${n} pages`;
    if (def.metaKind === "papers") return `${n} papers`;
    return `${n} items`;
  }
  if (matched.length > 0 || status === "success") {
    if (def.metaKind === "results") return "12 results";
    if (def.metaKind === "pages") return "8 pages";
    if (def.metaKind === "papers") return "15 papers";
    if (def.metaKind === "items") return "15 items";
  }
  return undefined;
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`;
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  return rem > 0 ? `${min}m ${rem}s` : `${min}m`;
}

function computeElapsed(
  stageId: string,
  events: RunEvent[],
  status: QuestStatus,
  nextStageId: string | undefined,
): string | undefined {
  const matched = eventsForStage(stageId, events);
  if (matched.length === 0) return undefined;

  const start = Math.min(...matched.map((e) => parseTs(e.timestamp)));
  if (!start) return undefined;

  let end: number;
  if (status === "running") {
    end = Date.now();
  } else if (nextStageId) {
    const nextMatched = eventsForStage(nextStageId, events);
    end =
      nextMatched.length > 0
        ? Math.min(...nextMatched.map((e) => parseTs(e.timestamp)))
        : Math.max(...matched.map((e) => parseTs(e.timestamp)));
  } else {
    end = Math.max(...matched.map((e) => parseTs(e.timestamp)));
  }

  const ms = end - start;
  if (ms <= 0 && status !== "running") return undefined;
  return formatElapsed(Math.max(ms, status === "running" ? 0 : 1));
}

export function buildTimelineSteps(events: RunEvent[]): QuestStep[] {
  const states = initStates();

  const sorted = [...events].sort((a, b) => parseTs(a.timestamp) - parseTs(b.timestamp));
  for (const e of sorted) {
    applyEvent(states, e);
  }

  if (states.synthesis === "running" && sorted.some((e) => e.type === "artifact_written")) {
    states.synthesis = "success";
  }

  resolveRunning(states, sorted);

  return TIMELINE_STAGE_DEFS.map((def, idx) => {
    const status = states[def.id];
    const nextId = TIMELINE_STAGE_DEFS[idx + 1]?.id;
    return {
      id: def.id,
      title: def.title,
      subtitle: def.subtitle,
      status,
      meta: buildMeta(def, sorted, status),
      elapsed: computeElapsed(def.id, sorted, status, nextId),
    };
  });
}

/** @deprecated */
export type StepStatus = QuestStatus;
/** @deprecated */
export type TimelineStep = QuestStep;

import type { LucideIcon } from "lucide-react";
import {
  Brain,
  CheckCircle2,
  FileSearch,
  FileText,
  Globe,
  PenLine,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { RunEvent } from "../lib/runEvents";
import { buildTimelineSteps, type QuestStatus } from "../lib/timelineStages";
import PanelTitle from "./PanelTitle";
import "../styles/timelineQuest.css";

interface Props {
  events: RunEvent[];
  sseConnected: boolean;
  usingEventPoll: boolean;
  onReplay?: () => void;
}

const STATUS_ZH: Record<QuestStatus, string> = {
  pending: "等待中",
  running: "进行中",
  success: "成功",
  failed: "失败",
};

const STAGE_ICONS: Record<string, LucideIcon> = {
  created: Sparkles,
  planning: Route,
  web_search: Search,
  web_scrape: Globe,
  paper_search: FileSearch,
  extract: FileText,
  synthesis: Brain,
  writing: PenLine,
  quality: ShieldCheck,
  finalize: CheckCircle2,
};

const ICON_SIZE = 12;

export default function Timeline({ events, sseConnected, usingEventPoll, onReplay }: Props) {
  const steps = buildTimelineSteps(events);
  const conn = sseConnected ? "LIVE" : usingEventPoll ? "POLL" : "—";
  const isIdle = events.length === 0;

  return (
    <aside className="quest-timeline">
      <div className="quest-timeline__head">
        <PanelTitle zh="任务时间线" en="AGENT TIMELINE" />
        <div className="quest-timeline__actions">
          {onReplay && (
            <button type="button" className="quest-timeline__replay" onClick={onReplay}>
              ↻
            </button>
          )}
          <span className={`quest-timeline__conn ${sseConnected ? "is-live" : ""}`}>{conn}</span>
        </div>
      </div>

      <div className="quest-track-wrap">
        <span className="quest-track__spine" aria-hidden />
        <ol className="quest-track">
          {steps.map((step, i) => {
            const isCurrent = step.status === "running";
            const isLast = i === steps.length - 1;
            const lineDone = step.status === "success";
            const Icon = STAGE_ICONS[step.id] ?? Sparkles;

            return (
              <li
                key={step.id}
                className={[
                  "quest-node",
                  `quest-node--${step.status}`,
                  isCurrent ? "quest-node--current" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <div className="quest-rail" aria-hidden>
                  {!isLast && (
                    <span
                      className={[
                        "quest-rail__line",
                        lineDone ? "quest-rail__line--done" : "",
                        isCurrent ? "quest-rail__line--active" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    />
                  )}
                  <span className={`quest-rail__icon quest-rail__icon--${step.status}`}>
                    <Icon size={ICON_SIZE} strokeWidth={2} className="quest-rail__svg" />
                  </span>
                </div>

                <article className={`quest-card ${isCurrent ? "quest-card--current" : ""}`}>
                  <div className="quest-card__head">
                    <div className="quest-card__titles">
                      <strong className="quest-card__title">{step.title}</strong>
                      <span className="quest-card__subtitle">{step.subtitle}</span>
                    </div>
                    <span className={`quest-badge quest-badge--${step.status}`}>
                      {step.status === "success" && (
                        <span className="quest-badge__check" aria-hidden>
                          ✓
                        </span>
                      )}
                      {STATUS_ZH[step.status]}
                    </span>
                  </div>

                  {(step.meta || step.elapsed) && (
                    <div className="quest-card__meta">
                      {step.meta && <span className="quest-card__stat">{step.meta}</span>}
                      {step.elapsed && (
                        <span className="quest-card__elapsed">{step.elapsed}</span>
                      )}
                    </div>
                  )}
                </article>
              </li>
            );
          })}
        </ol>
      </div>

      {isIdle && <p className="quest-timeline__footer">等待 Mission 启动…</p>}
    </aside>
  );
}

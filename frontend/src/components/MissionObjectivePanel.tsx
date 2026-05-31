import type { RunStatusSnapshot } from "../lib/taskTypes";
import { displayText } from "../lib/display";
import MissionComposer from "./MissionComposer";

interface Props {
  status: RunStatusSnapshot | null;
  runId: string | null;
  starting: boolean;
  restoring: boolean;
  error: string | null;
  onStart: (scenario: string, goal?: string) => void;
}

export default function MissionObjectivePanel({
  status,
  runId,
  starting,
  restoring,
  error,
  onStart,
}: Props) {
  const goal = displayText(status?.goal, "选择场景并启动 Mission…");
  const hasRun = Boolean(status?.goal && runId);

  return (
    <section className="hud-panel hud-panel--mission">
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />
      <span className="hud-panel__decor">OBJ-01 // MISSION BRIEF</span>

      <header className="hud-panel__head">
        <span className="hud-panel__diamond" aria-hidden />
        <div className="hud-panel__titles">
          <h3 className="hud-panel__title">任务目标</h3>
          <span className="hud-panel__subtitle">MISSION OBJECTIVE</span>
        </div>
      </header>

      <div className="hud-panel__body">
        <div className="hud-panel__main">
          <div className="hud-panel__brief">
            <p className="hud-panel__brief-text">{goal}</p>
          </div>
          <div className="hud-panel__tags">
            <span className="hud-capsule hud-capsule--blue">
              <span className="hud-capsule__icon" aria-hidden />
              模式：{displayText(status?.taskType, "Research")}
            </span>
            <span className="hud-capsule hud-capsule--purple">
              <span className="hud-capsule__icon hud-capsule__icon--sq" aria-hidden />
              深度：Deep
            </span>
            <span className="hud-capsule hud-capsule--violet">
              <span className="hud-capsule__icon hud-capsule__icon--node" aria-hidden />
              来源：Web + Papers
            </span>
            <span className="hud-capsule hud-capsule--gold">
              <span className="hud-capsule__icon hud-capsule__icon--tri" aria-hidden />
              输出格式：Markdown
            </span>
          </div>
        </div>

        {!hasRun && (
          <div className="hud-panel__launch">
            <MissionComposer
              variant="hud"
              runId={runId}
              onStart={onStart}
              starting={starting}
              restoring={restoring}
              error={error}
            />
          </div>
        )}
      </div>
    </section>
  );
}

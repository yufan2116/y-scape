import { useEffect, useState } from "react";
import { fetchDemoScenarios } from "../api/client";
import { formatUserError } from "../lib/display";
import type { DemoScenario } from "../lib/taskTypes";
import { withTimeout } from "../lib/withTimeout";
import PanelTitle from "./PanelTitle";

interface Props {
  runId: string | null;
  onStart: (scenario: string, goal?: string) => void;
  starting: boolean;
  restoring?: boolean;
  error?: string | null;
  variant?: "panel" | "compact" | "hud";
}

const SCENARIO_TIMEOUT_MS = 12_000;

export default function MissionComposer({
  runId,
  onStart,
  starting,
  restoring,
  error,
  variant = "panel",
}: Props) {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [scenario, setScenario] = useState("web_research_demo");
  const [goal, setGoal] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scenariosLoading, setScenariosLoading] = useState(true);

  useEffect(() => {
    setScenariosLoading(true);
    void withTimeout(fetchDemoScenarios(), SCENARIO_TIMEOUT_MS, "场景列表加载超时，请刷新页面")
      .then((list) => {
        setScenarios(list);
        if (list.length > 0) setScenario(list[0].name);
        setLoadError(null);
      })
      .catch((e) => setLoadError(formatUserError(e)))
      .finally(() => setScenariosLoading(false));
  }, []);

  const selected = scenarios.find((s) => s.name === scenario);
  const busy = starting || restoring || scenariosLoading;

  if (variant === "compact") {
    return (
      <div className="aos-mission-launch">
        {(loadError || error) && (
          <p className="error aos-launch-error">{loadError || error}</p>
        )}
        {restoring && <p className="muted">正在恢复上次会话…</p>}
        <div className="aos-launch-row">
          <select value={scenario} disabled={busy} onChange={(e) => setScenario(e.target.value)}>
            {scenariosLoading && <option value="">加载场景…</option>}
            {scenarios.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={goal}
            disabled={busy}
            placeholder={selected?.goal ?? "Goal override…"}
            onChange={(e) => setGoal(e.target.value)}
          />
          <button
            type="button"
            className="btn-primary aos-launch-btn hud-button"
            disabled={busy || !scenario}
            onClick={() => onStart(scenario, goal)}
          >
            {starting ? "启动中…" : restoring ? "恢复中…" : "▶ Launch Mission"}
          </button>
        </div>
      </div>
    );
  }

  if (variant === "hud") {
    return (
      <div className="sr-launch-hud">
        {(loadError || error) && (
          <p className="sr-launch-error">{loadError || error}</p>
        )}
        {restoring && <p className="sr-launch-hint">正在恢复上次会话…</p>}
        <div className="sr-launch-controls">
          <select
            className="sr-launch-select"
            value={scenario}
            disabled={busy}
            onChange={(e) => setScenario(e.target.value)}
          >
            {scenariosLoading && <option value="">加载场景…</option>}
            {scenarios.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            className="sr-launch-input"
            value={goal}
            disabled={busy}
            placeholder={selected?.goal ?? "目标覆盖…"}
            onChange={(e) => setGoal(e.target.value)}
          />
          <button
            type="button"
            className="sr-launch-btn hud-button"
            disabled={busy || !scenario}
            onClick={() => onStart(scenario, goal)}
          >
            {starting ? "启动中…" : restoring ? "恢复中…" : "▶ 启动任务"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="panel sr-mission-card">
      <PanelTitle zh="任务控制台" en="MISSION CONSOLE" />
      {restoring && <p className="muted">正在恢复上次会话…</p>}
      {loadError && <p className="error">{loadError}</p>}
      {error && <p className="error">{error}</p>}

      {selected && (
        <div className="sr-mission-goal">
          <p>{selected.goal}</p>
          <div className="sr-pill-row">
            <span className="sr-pill sr-pill-blue">{selected.taskType}</span>
            <span className="sr-pill sr-pill-purple">{selected.name}</span>
          </div>
        </div>
      )}

      <label className="field">
        <span className="label">Demo 场景 · SCENARIO</span>
        <select value={scenario} disabled={busy} onChange={(e) => setScenario(e.target.value)}>
          {scenariosLoading && <option value="">加载场景…</option>}
          {scenarios.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      {selected && <p className="muted">{selected.description}</p>}

      <label className="field">
        <span className="label">目标覆盖 · GOAL OVERRIDE</span>
        <input
          type="text"
          value={goal}
          disabled={busy}
          placeholder={selected?.goal ?? "输入任务目标…"}
          onChange={(e) => setGoal(e.target.value)}
        />
      </label>

      <button
        type="button"
        className="btn-primary sr-btn-launch hud-button"
        disabled={busy || !scenario}
        onClick={() => onStart(scenario, goal)}
      >
        {starting ? "启动中…" : restoring ? "恢复中…" : "▶ 创建并启动任务"}
      </button>

      <div className="run-id-row">
        <span className="label">Run ID</span>
        <code className="sr-truncate" title={runId ?? undefined}>
          {runId ?? "—"}
        </code>
      </div>
    </section>
  );
}

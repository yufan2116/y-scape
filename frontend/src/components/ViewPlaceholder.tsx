import type { ActiveView } from "../lib/viewNav";
import { VIEW_META } from "../lib/viewNav";
import PanelTitle from "./PanelTitle";
import "../styles/viewPlaceholder.css";

interface Props {
  view: Exclude<ActiveView, "dashboard">;
}

export default function ViewPlaceholder({ view }: Props) {
  const meta = VIEW_META[view];

  return (
    <section className="view-placeholder glass-panel aos-glass" aria-labelledby={`view-${view}-title`}>
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />

      <header className="view-placeholder__head">
        <PanelTitle zh={meta.zh} en={meta.en} />
      </header>

      <div className="view-placeholder__body">
        <div className="view-placeholder__icon" aria-hidden>
          <span className="view-placeholder__icon-ring" />
          <span className="view-placeholder__icon-core" />
        </div>
        <h2 className="view-placeholder__headline" id={`view-${view}-title`}>
          {meta.headline}
        </h2>
        <p className="view-placeholder__desc">{meta.description}</p>
        {meta.hint && <p className="view-placeholder__hint">{meta.hint}</p>}
        <p className="view-placeholder__status">模块占位 · Placeholder view</p>
      </div>
    </section>
  );
}

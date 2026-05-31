import { useState } from "react";
import "../styles/agentProfileCard.css";

export type AgentHealth = "stable" | "warning" | "error";

export type AgentProfileCardProps = {
  avatarUrl?: string;
  agentName?: string;
  agentType?: string;
  modelName?: string;
  memoryPercent?: number;
  health?: AgentHealth;
  saveEnabled?: boolean;
  quote?: string;
  compact?: boolean;
};

const DEFAULT_AVATAR = "/assets/avatar/agent.png";

const HEALTH_LABEL: Record<AgentHealth, string> = {
  stable: "Stable",
  warning: "Warn",
  error: "Critical",
};

function StatusChip({
  label,
  value,
  valueClass = "",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="agent-status-chip">
      <span className="agent-status-chip__label">{label}</span>
      <span className={`agent-status-chip__value ${valueClass}`.trim()}>{value}</span>
    </div>
  );
}

export default function AgentProfileCard({
  avatarUrl = DEFAULT_AVATAR,
  agentName = "Y-Space Agent",
  agentType = "RESEARCH AGENT",
  modelName = "Demo",
  memoryPercent = 12,
  health = "stable",
  saveEnabled = true,
  quote = "Research core online.",
  compact = false,
}: AgentProfileCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(avatarUrl) && !imageFailed;
  const memory = Math.min(100, Math.max(0, memoryPercent));
  const healthClass = `agent-status-chip__value--health-${health}`;

  return (
    <section className="agent-profile-card" aria-label="Agent Profile">
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />

      <div className="agent-profile-card__avatar-section">
        <div className="agent-avatar-frame">
          <span className="agent-avatar-orbit agent-avatar-orbit--outer" aria-hidden />
          <span className="agent-avatar-orbit agent-avatar-orbit--inner" aria-hidden />
          <div className="agent-avatar-orbit__core">
            {showImage ? (
              <img
                className="agent-avatar-image"
                src={avatarUrl}
                alt=""
                onError={() => setImageFailed(true)}
              />
            ) : (
              <div className="agent-avatar-placeholder" aria-hidden>
                <span className="agent-avatar-placeholder__silhouette" />
                <span className="agent-avatar-placeholder__glow" />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="agent-profile-card__identity">
        <h3 className="agent-profile-name" title={agentName}>
          {agentName}
        </h3>
        <p className="agent-profile-type">{agentType}</p>
      </div>

      <div className={`agent-status-chips${compact ? " agent-status-chips--compact" : ""}`}>
        {!compact && (
          <StatusChip label="Model" value={modelName} valueClass="agent-status-chip__value--cyan" />
        )}
        <StatusChip
          label="Memory"
          value={`${memory}%`}
          valueClass="agent-status-chip__value--gold"
        />
        <StatusChip
          label="Health"
          value={HEALTH_LABEL[health]}
          valueClass={healthClass}
        />
        <StatusChip
          label="Save"
          value={saveEnabled ? "On" : "Off"}
          valueClass="agent-status-chip__value--gold"
        />
        {compact && (
          <StatusChip label="Model" value={modelName} valueClass="agent-status-chip__value--cyan" />
        )}
      </div>

      <p className="agent-profile-quote">{quote}</p>
    </section>
  );
}

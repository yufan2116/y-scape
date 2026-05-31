import type { ArtifactMeta } from "../lib/taskTypes";
import { displayText } from "../lib/display";
import ArtifactFileItem, { type ArtifactFileKind } from "./ArtifactFileItem";
import "../styles/artifactPanel.css";

interface Props {
  artifacts: ArtifactMeta[];
  onPreview: (name: string) => void;
  selected?: string;
  loading?: boolean;
}

function detectFileKind(name: string, type?: string): ArtifactFileKind {
  const lower = (name || "").toLowerCase();
  const typeLower = (type || "").toLowerCase();

  if (
    lower.endsWith(".md") ||
    lower.endsWith(".markdown") ||
    typeLower.includes("markdown")
  ) {
    return "markdown";
  }
  if (lower.endsWith(".json") || typeLower.includes("json")) return "json";
  if (lower.endsWith(".bib") || typeLower.includes("bib")) return "bib";
  if (lower.endsWith(".pdf") || typeLower.includes("pdf")) return "pdf";
  if (lower.endsWith(".txt") || typeLower.includes("text/plain")) return "txt";
  return "default";
}

function formatTypeLabel(kind: ArtifactFileKind, name: string): string {
  const map: Record<ArtifactFileKind, string> = {
    markdown: "Markdown",
    json: "JSON",
    bib: "BIB",
    pdf: "PDF",
    txt: "TXT",
    default: "File",
  };
  if (map[kind] !== "File") return map[kind];

  const dot = name.lastIndexOf(".");
  if (dot > 0 && dot < name.length - 1) {
    return name.slice(dot + 1).toUpperCase();
  }
  return "File";
}

function formatSize(size: unknown): string {
  if (typeof size !== "number" || !Number.isFinite(size) || size < 0) {
    return "Unknown size";
  }
  if (size < 1024) return `${size} B`;
  return `${(size / 1024).toFixed(1)} KB`;
}

function formatRelativeTime(iso?: string | null): string {
  if (!iso) return "just now";

  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "just now";

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 60_000) return "just now";

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function resolveTimestamp(artifact: ArtifactMeta): string {
  const extended = artifact as ArtifactMeta & { updatedAt?: string | null };
  return extended.updatedAt ?? artifact.createdAt ?? "";
}

export default function ArtifactExplorer({ artifacts, onPreview, selected, loading }: Props) {
  const count = artifacts.length;

  return (
    <div className="artifact-panel">
      <header className="artifact-header">
        <div className="artifact-header__left">
          <span className="hud-panel__diamond" aria-hidden />
          <div className="artifact-header__titles">
            <h2 className="artifact-title">产物列表（{count}）</h2>
            <span className="artifact-subtitle">ARTIFACTS</span>
          </div>
        </div>
        <button type="button" className="artifact-view-all hud-button" disabled={count === 0}>
          查看全部
        </button>
      </header>

      {count === 0 ? (
        <div className="artifact-empty">
          <span className="artifact-empty__icon" aria-hidden />
          <p className="artifact-empty__text">暂无交付物 · No artifacts yet</p>
        </div>
      ) : (
        <div className="artifact-list">
          {artifacts.map((artifact) => {
            const name = displayText(artifact.name);
            const kind = detectFileKind(artifact.name, artifact.type);

            return (
              <ArtifactFileItem
                key={artifact.name}
                name={name}
                typeLabel={formatTypeLabel(kind, artifact.name)}
                sizeLabel={formatSize(artifact.size)}
                timeLabel={formatRelativeTime(resolveTimestamp(artifact))}
                kind={kind}
                selected={selected === artifact.name}
                loading={loading}
                onSelect={() => onPreview(artifact.name)}
                onPreview={() => onPreview(artifact.name)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

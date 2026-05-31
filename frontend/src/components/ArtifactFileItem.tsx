import { Eye, FileText } from "lucide-react";

export type ArtifactFileKind = "markdown" | "json" | "bib" | "pdf" | "txt" | "default";

interface Props {
  name: string;
  typeLabel: string;
  sizeLabel: string;
  timeLabel: string;
  kind: ArtifactFileKind;
  selected: boolean;
  loading?: boolean;
  onSelect: () => void;
  onPreview: () => void;
}

export default function ArtifactFileItem({
  name,
  typeLabel,
  sizeLabel,
  timeLabel,
  kind,
  selected,
  loading,
  onSelect,
  onPreview,
}: Props) {
  return (
    <div
      className={`artifact-file-item${selected ? " is-selected" : ""}`}
      role="button"
      tabIndex={0}
      onClick={() => !loading && onSelect()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (!loading) onSelect();
        }
      }}
    >
      <div className={`artifact-file-icon ${kind}`} aria-hidden>
        <FileText size={20} strokeWidth={1.75} />
      </div>

      <div className="artifact-file-main">
        <div className="artifact-file-name">{name}</div>
        <div className="artifact-file-meta">
          {typeLabel} · {sizeLabel} · {timeLabel}
        </div>
      </div>

      <button
        type="button"
        className="artifact-preview-button"
        title="预览"
        aria-label={`预览 ${name}`}
        disabled={loading}
        onClick={(e) => {
          e.stopPropagation();
          onPreview();
        }}
      >
        <Eye size={16} strokeWidth={1.75} />
      </button>
    </div>
  );
}

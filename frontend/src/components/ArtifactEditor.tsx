import type { ArtifactMeta } from "../lib/taskTypes";
import ArtifactExplorer from "./ArtifactExplorer";
import MarkdownPreview from "./MarkdownPreview";

interface Props {
  artifacts: ArtifactMeta[];
  onPreview: (name: string) => void;
  selected?: string;
  previewLoading?: boolean;
  content: string;
  filename: string;
  contentType?: string;
  previewError?: string | null;
}

export default function ArtifactEditor({
  artifacts,
  onPreview,
  selected,
  previewLoading,
  content,
  filename,
  contentType,
  previewError,
}: Props) {
  return (
    <div className="aos-artifact-col">
      <section className="glass-panel aos-artifacts-panel aos-glass">
        <ArtifactExplorer
          artifacts={artifacts}
          onPreview={onPreview}
          selected={selected}
          loading={previewLoading}
        />
      </section>

      <section className="glass-panel aos-preview-panel aos-glass">
        <MarkdownPreview
          content={content}
          filename={filename}
          contentType={contentType}
          loading={previewLoading}
          error={previewError}
        />
      </section>
    </div>
  );
}

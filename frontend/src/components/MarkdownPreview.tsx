import ReactMarkdown from "react-markdown";
import { displayText } from "../lib/display";
import PanelTitle from "./PanelTitle";

interface Props {
  content: string;
  filename: string;
  contentType?: string;
  loading?: boolean;
  error?: string | null;
}

function isMarkdown(filename: string, contentType?: string): boolean {
  if (contentType?.includes("markdown")) return true;
  const lower = filename.toLowerCase();
  return lower.endsWith(".md") || lower.endsWith(".markdown");
}

function isJson(filename: string, contentType?: string): boolean {
  if (contentType?.includes("json")) return true;
  return filename.toLowerCase().endsWith(".json");
}

function contentStats(content: string) {
  const lines = content ? content.split("\n").length : 0;
  const words = content ? content.trim().split(/\s+/).filter(Boolean).length : 0;
  const chars = content.length;
  return { lines, words, chars };
}

export default function MarkdownPreview({
  content,
  filename,
  contentType,
  loading,
  error,
}: Props) {
  const hasFile = Boolean(filename);
  const hasContent = Boolean(content);
  const stats = contentStats(content);
  const displayName = displayText(filename, "preview.md");

  return (
    <>
      <div className="aos-preview-chrome">
        <PanelTitle zh={`预览：${displayName}`} en="MARKDOWN PREVIEW" />
        <div className="aos-window-dots" aria-hidden>
          <span />
          <span />
          <span />
        </div>
      </div>

      <div className="aos-preview-body-wrap">
        {loading && <p className="muted">加载中…</p>}
        {error && (
          <div className="preview-error">
            <strong>预览失败</strong>
            <p>{displayText(error)}</p>
          </div>
        )}

        {!loading && !error && !hasContent && !hasFile && (
          <p className="muted">选择文件预览</p>
        )}

        {!loading && !error && hasContent && isMarkdown(filename, contentType) && (
          <article className="markdown-body">
            <ReactMarkdown>{content}</ReactMarkdown>
          </article>
        )}

        {!loading && !error && hasContent && isJson(filename, contentType) && (
          <pre className="code-preview">{formatJson(content)}</pre>
        )}

        {!loading &&
          !error &&
          hasContent &&
          !isMarkdown(filename, contentType) &&
          !isJson(filename, contentType) && (
            <pre className="code-preview">{content}</pre>
          )}
      </div>

      {hasContent && (
        <footer className="aos-preview-stats">
          <span>Lines {stats.lines.toLocaleString()}</span>
          <span>Words {stats.words.toLocaleString()}</span>
          <span>Chars {stats.chars.toLocaleString()}</span>
        </footer>
      )}
    </>
  );
}

function formatJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

import { useCallback, useEffect, useMemo, useState } from "react";
import PanelTitle from "../components/PanelTitle";
import ToolCard from "../components/tools/ToolCard";
import ToolWorkspace from "../components/tools/ToolWorkspace";
import ArtifactExplorer from "../components/ArtifactExplorer";
import MarkdownPreview from "../components/MarkdownPreview";
import {
  fetchNativeArtifactContent,
  fetchNativeToolArtifacts,
  fetchNativeTools,
} from "../api/nativeTools";
import type { ArtifactMeta } from "../lib/taskTypes";
import type {
  NativeToolArtifact,
  NativeToolDefinition,
  NativeToolRunResult,
} from "../lib/nativeToolTypes";
import { NATIVE_TOOL_CATEGORIES } from "../lib/nativeToolTypes";
import "../styles/toolHub.css";

export default function ToolHubView() {
  const [tools, setTools] = useState<NativeToolDefinition[]>([]);
  const [selectedId, setSelectedId] = useState<string>("markdown_convert");
  const [artifacts, setArtifacts] = useState<NativeToolArtifact[]>([]);
  const [previewName, setPreviewName] = useState("");
  const [previewContent, setPreviewContent] = useState("");
  const [previewType, setPreviewType] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [toolList, artifactList] = await Promise.all([
      fetchNativeTools(),
      fetchNativeToolArtifacts(),
    ]);
    setTools(toolList);
    setArtifacts(artifactList);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedTool = useMemo(
    () => tools.find((t) => t.toolId === selectedId) ?? null,
    [tools, selectedId],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, NativeToolDefinition[]>();
    for (const cat of NATIVE_TOOL_CATEGORIES) map.set(cat, []);
    for (const tool of tools) {
      const list = map.get(tool.category) ?? [];
      list.push(tool);
      map.set(tool.category, list);
    }
    return map;
  }, [tools]);

  const artifactMeta: ArtifactMeta[] = useMemo(
    () =>
      artifacts.map((a) => ({
        name: a.name,
        type: a.type,
        path: a.url,
        url: a.url,
        size: a.size,
        createdAt: a.createdAt ?? new Date().toISOString(),
      })),
    [artifacts],
  );

  const handleResult = (result: NativeToolRunResult) => {
    if (result.ok) {
      setLastMessage(result.message ?? "Done");
      if (result.artifacts?.length) {
        setArtifacts((prev) => {
          const merged = [...result.artifacts!, ...prev];
          const seen = new Set<string>();
          return merged.filter((a) => {
            const key = `${a.jobId ?? ""}:${a.name}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
        });
        const first = result.artifacts[0];
        if (first.jobId) {
          void openPreview(first.jobId, first.name);
        }
      }
    } else {
      setLastMessage(result.error ?? "Failed");
    }
    void load();
  };

  const openPreview = async (jobId: string, name: string) => {
    setPreviewName(name);
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const data = await fetchNativeArtifactContent(jobId, name);
      setPreviewContent(data.content);
      setPreviewType(data.contentType);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
      setPreviewContent("");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handlePreview = (name: string) => {
    const art = artifacts.find((a) => a.name === name);
    if (art?.jobId) void openPreview(art.jobId, name);
  };

  return (
    <section className="tool-hub-native glass-panel aos-glass">
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />

      <header className="tool-hub-native__head">
        <PanelTitle zh="工具中心" en="TOOL HUB" />
        <button type="button" className="hud-button sr-btn-ghost" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      {lastMessage && <p className="tool-hub-native__toast muted">{lastMessage}</p>}

      <div className="tool-hub-native__layout">
        <aside className="tool-hub-native__list">
          {NATIVE_TOOL_CATEGORIES.map((cat) => {
            const items = grouped.get(cat) ?? [];
            if (!items.length) return null;
            return (
              <section key={cat} className="tool-hub-native__group">
                <h3>{cat}</h3>
                {items.map((tool) => (
                  <ToolCard
                    key={tool.toolId}
                    tool={tool}
                    active={selectedId === tool.toolId}
                    onSelect={setSelectedId}
                  />
                ))}
              </section>
            );
          })}
        </aside>

        <div className="tool-hub-native__center">
          <ToolWorkspace tool={selectedTool} onResult={handleResult} />
        </div>

        <aside className="tool-hub-native__artifacts aos-artifact-col">
          <section className="glass-panel aos-artifacts-panel aos-glass tool-hub-native__artifact-list">
            <h4 className="tool-hub-native__artifact-title">Tool Artifacts</h4>
            <ArtifactExplorer
              artifacts={artifactMeta}
              onPreview={handlePreview}
              selected={previewName}
              loading={previewLoading}
            />
          </section>
          <section className="glass-panel aos-preview-panel aos-glass">
            <MarkdownPreview
              content={previewContent}
              filename={previewName}
              contentType={previewType}
              loading={previewLoading}
              error={previewError}
            />
          </section>
        </aside>
      </div>
    </section>
  );
}

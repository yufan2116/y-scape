import { useCallback, useEffect, useState } from "react";
import PanelTitle from "../components/PanelTitle";
import { fetchSystemSettings, saveSystemSettings } from "../api/nativeTools";
import type { SystemSettings } from "../lib/nativeToolTypes";
import "../styles/toolSettings.css";

const ALL_TOOLS = [
  "markdown_convert",
  "folder_clean",
  "github_resume_generator",
  "local_rag_query",
  "bilibili_download",
  "quickforge_launcher",
];

export default function SettingsView() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSystemSettings();
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载设置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const patch = (section: keyof SystemSettings, key: string, value: unknown) => {
    if (!settings) return;
    setSettings({
      ...settings,
      [section]: { ...(settings[section] as Record<string, unknown>), [key]: value },
    });
  };

  const toggleTool = (toolId: string) => {
    if (!settings) return;
    const enabled = new Set(settings.tool.enabledTools);
    if (enabled.has(toolId)) enabled.delete(toolId);
    else enabled.add(toolId);
    patch("tool", "enabledTools", Array.from(enabled));
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSavedMsg(null);
    try {
      const saved = await saveSystemSettings(settings);
      setSettings(saved);
      setSavedMsg("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading && !settings) {
    return <p className="settings-view__loading muted">Loading system settings…</p>;
  }

  if (!settings) {
    return <p className="error">{error ?? "无法加载设置"}</p>;
  }

  return (
    <section className="settings-view glass-panel aos-glass">
      <span className="hud-panel__corner hud-panel__corner--tl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--tr" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--bl" aria-hidden />
      <span className="hud-panel__corner hud-panel__corner--br" aria-hidden />

      <header className="settings-view__head">
        <PanelTitle zh="系统设置" en="SETTINGS" />
        <button type="button" className="hud-button" disabled={saving} onClick={() => void handleSave()}>
          {saving ? "Saving…" : "Save All"}
        </button>
      </header>

      {error && <p className="error">{error}</p>}
      {savedMsg && <p className="settings-view__saved">{savedMsg}</p>}

      <div className="settings-view__grid">
        <article className="settings-section hud-panel">
          <h3>Model Settings</h3>
          <label className="field">
            <span className="label">Provider</span>
            <input
              value={settings.model.provider}
              onChange={(e) => patch("model", "provider", e.target.value)}
            />
          </label>
          <label className="field">
            <span className="label">Model Name</span>
            <input
              value={settings.model.modelName}
              onChange={(e) => patch("model", "modelName", e.target.value)}
            />
          </label>
          <p className="muted">
            API Key: {settings.model.apiKeyConfigured ? "Configured" : "Not configured"}
          </p>
          <label className="settings-view__toggle field">
            <input
              type="checkbox"
              checked={settings.model.demoMode}
              onChange={(e) => patch("model", "demoMode", e.target.checked)}
            />
            <span>Demo Mode</span>
          </label>
        </article>

        <article className="settings-section hud-panel">
          <h3>Storage Settings</h3>
          <label className="field">
            <span className="label">Workspace Root</span>
            <input
              value={settings.storage.workspaceRoot}
              onChange={(e) => patch("storage", "workspaceRoot", e.target.value)}
            />
          </label>
          <label className="field">
            <span className="label">Artifact Root</span>
            <input
              value={settings.storage.artifactRoot}
              onChange={(e) => patch("storage", "artifactRoot", e.target.value)}
            />
          </label>
          <label className="field">
            <span className="label">Max Artifact Size (MB)</span>
            <input
              type="number"
              min={1}
              value={settings.storage.maxArtifactSizeMb}
              onChange={(e) => patch("storage", "maxArtifactSizeMb", Number(e.target.value))}
            />
          </label>
        </article>

        <article className="settings-section hud-panel">
          <h3>Tool Settings</h3>
          <p className="label">Enabled Tools</p>
          <div className="settings-view__tool-list">
            {ALL_TOOLS.map((id) => (
              <label key={id} className="settings-view__toggle">
                <input
                  type="checkbox"
                  checked={settings.tool.enabledTools.includes(id)}
                  onChange={() => toggleTool(id)}
                />
                <code>{id}</code>
              </label>
            ))}
          </div>
          <label className="field">
            <span className="label">Default Output Directory</span>
            <input
              value={settings.tool.defaultOutputDirectory}
              onChange={(e) => patch("tool", "defaultOutputDirectory", e.target.value)}
            />
          </label>
          <label className="settings-view__toggle field">
            <input
              type="checkbox"
              checked={settings.tool.dryRunDefault}
              onChange={(e) => patch("tool", "dryRunDefault", e.target.checked)}
            />
            <span>Dry Run Default</span>
          </label>
        </article>

        <article className="settings-section hud-panel">
          <h3>Runtime Settings</h3>
          <label className="field">
            <span className="label">Max Iterations</span>
            <input
              type="number"
              min={1}
              value={settings.runtime.maxIterations}
              onChange={(e) => patch("runtime", "maxIterations", Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span className="label">Planner Timeout (s)</span>
            <input
              type="number"
              min={1}
              value={settings.runtime.plannerTimeoutSeconds}
              onChange={(e) => patch("runtime", "plannerTimeoutSeconds", Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span className="label">Tool Timeout (s)</span>
            <input
              type="number"
              min={1}
              value={settings.runtime.toolTimeoutSeconds}
              onChange={(e) => patch("runtime", "toolTimeoutSeconds", Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span className="label">Status Polling Interval (ms)</span>
            <input
              type="number"
              min={500}
              value={settings.runtime.statusPollingIntervalMs}
              onChange={(e) => patch("runtime", "statusPollingIntervalMs", Number(e.target.value))}
            />
          </label>
        </article>
      </div>
    </section>
  );
}

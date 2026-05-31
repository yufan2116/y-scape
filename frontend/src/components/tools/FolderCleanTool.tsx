import { useState } from "react";
import { scanFolder } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function FolderCleanTool({ onResult }: Props) {
  const [targetPath, setTargetPath] = useState(".");
  const [scanMode, setScanMode] = useState("all");
  const [dryRun, setDryRun] = useState(true);
  const [maxDepth, setMaxDepth] = useState(8);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await scanFolder({
        target_path: targetPath,
        scan_mode: scanMode,
        dry_run: dryRun,
        max_depth: maxDepth,
      });
      onResult(result);
      if (!result.ok) setError(result.error ?? "扫描失败");
    } catch (err) {
      setError(err instanceof Error ? err.message : "扫描失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <label className="field">
        <span className="label">Target Path</span>
        <input value={targetPath} onChange={(e) => setTargetPath(e.target.value)} placeholder="D:\projects\my-folder" />
      </label>

      <label className="field">
        <span className="label">Scan Mode</span>
        <select value={scanMode} onChange={(e) => setScanMode(e.target.value)}>
          <option value="all">All (empty + large + duplicates)</option>
          <option value="empty_dirs">Empty directories</option>
          <option value="large_files">Large files</option>
          <option value="duplicates">Duplicate files</option>
        </select>
      </label>

      <label className="field">
        <span className="label">Max Depth</span>
        <input
          type="number"
          min={1}
          max={32}
          value={maxDepth}
          onChange={(e) => setMaxDepth(Number(e.target.value) || 8)}
        />
      </label>

      <label className="native-tool-form__toggle field">
        <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
        <span>Dry Run (default — no files deleted)</span>
      </label>

      {error && <p className="error">{error}</p>}

      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Scanning…" : "Scan"}
      </button>
    </form>
  );
}

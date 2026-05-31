import { useState } from "react";
import { downloadBilibiliStub } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function BilibiliToolStub({ onResult }: Props) {
  const [url, setUrl] = useState("");
  const [outputDir, setOutputDir] = useState("./downloads");
  const [quality, setQuality] = useState("1080p");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await downloadBilibiliStub({ url, output_dir: outputDir, quality });
      onResult(result);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <p className="warn">Stub — Bilibili download integration coming soon.</p>
      <label className="field">
        <span className="label">URL / BV</span>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.bilibili.com/video/BV..." />
      </label>
      <label className="field">
        <span className="label">Output Directory</span>
        <input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} />
      </label>
      <label className="field">
        <span className="label">Quality</span>
        <select value={quality} onChange={(e) => setQuality(e.target.value)}>
          <option value="1080p">1080p</option>
          <option value="720p">720p</option>
          <option value="480p">480p</option>
        </select>
      </label>
      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Processing…" : "Download (Stub)"}
      </button>
    </form>
  );
}

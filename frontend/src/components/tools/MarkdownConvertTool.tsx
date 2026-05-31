import { useState } from "react";
import { convertMarkdown } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function MarkdownConvertTool({ onResult }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState("auto");
  const [outputFilename, setOutputFilename] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("请选择要转换的文件");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("source_type", sourceType === "auto" ? file.name.split(".").pop() ?? "txt" : sourceType);
      form.append("output_filename", outputFilename);
      const result = await convertMarkdown(form);
      onResult(result);
      if (!result.ok) setError(result.error ?? "转换失败");
    } catch (err) {
      setError(err instanceof Error ? err.message : "转换失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <label className="field">
        <span className="label">Upload File</span>
        <input
          type="file"
          accept=".txt,.md,.html,.htm,.pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <label className="field">
        <span className="label">Source Type</span>
        <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
          <option value="auto">Auto detect</option>
          <option value="txt">TXT</option>
          <option value="html">HTML</option>
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
        </select>
      </label>

      <label className="field">
        <span className="label">Output Filename</span>
        <input
          value={outputFilename}
          onChange={(e) => setOutputFilename(e.target.value)}
          placeholder="converted.md"
        />
      </label>

      {error && <p className="error">{error}</p>}

      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Converting…" : "Convert"}
      </button>
    </form>
  );
}

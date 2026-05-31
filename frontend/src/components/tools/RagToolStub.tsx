import { useState } from "react";
import { queryRagStub } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function RagToolStub({ onResult }: Props) {
  const [documentPath, setDocumentPath] = useState(".");
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [model, setModel] = useState("ollama");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await queryRagStub({
        document_path: documentPath,
        question,
        top_k: topK,
        model,
      });
      onResult(result);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <p className="warn">Stub — full RAG indexing coming soon.</p>
      <label className="field">
        <span className="label">Document Path</span>
        <input value={documentPath} onChange={(e) => setDocumentPath(e.target.value)} />
      </label>
      <label className="field">
        <span className="label">Question</span>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} />
      </label>
      <label className="field">
        <span className="label">Top K</span>
        <input type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
      </label>
      <label className="field">
        <span className="label">Model</span>
        <input value={model} onChange={(e) => setModel(e.target.value)} />
      </label>
      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Querying…" : "Query (Stub)"}
      </button>
    </form>
  );
}

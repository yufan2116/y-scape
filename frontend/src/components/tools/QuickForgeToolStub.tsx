import { useState } from "react";
import { runQuickForgeStub } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function QuickForgeToolStub({ onResult }: Props) {
  const [script, setScript] = useState("main.py");
  const [args, setArgs] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await runQuickForgeStub({
        script,
        args: args.split(/\s+/).filter(Boolean),
      });
      onResult(result);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <p className="warn">Stub — QuickForge script runner coming soon.</p>
      <label className="field">
        <span className="label">Script</span>
        <select value={script} onChange={(e) => setScript(e.target.value)}>
          <option value="main.py">main.py</option>
          <option value="launch.py">launch.py</option>
          <option value="run_script.py">run_script.py</option>
        </select>
      </label>
      <label className="field">
        <span className="label">Args</span>
        <input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="--flag value" />
      </label>
      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Running…" : "Run (Stub)"}
      </button>
    </form>
  );
}

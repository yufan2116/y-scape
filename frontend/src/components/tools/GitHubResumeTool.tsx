import { useState } from "react";
import { generateGitHubResume } from "../../api/nativeTools";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  onResult: (result: NativeToolRunResult) => void;
}

export default function GitHubResumeTool({ onResult }: Props) {
  const [repoUrl, setRepoUrl] = useState("https://github.com/octocat/Hello-World");
  const [language, setLanguage] = useState("zh");
  const [roleTarget, setRoleTarget] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await generateGitHubResume({
        repo_url: repoUrl,
        language,
        role_target: roleTarget,
      });
      onResult(result);
      if (!result.ok) setError(result.error ?? "生成失败");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="native-tool-form" onSubmit={(e) => void handleSubmit(e)}>
      <label className="field">
        <span className="label">GitHub Repo URL</span>
        <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repo" />
      </label>

      <label className="field">
        <span className="label">Language</span>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </label>

      <label className="field">
        <span className="label">Role Target</span>
        <input
          value={roleTarget}
          onChange={(e) => setRoleTarget(e.target.value)}
          placeholder="Software Engineer / 后端工程师"
        />
      </label>

      {error && <p className="error">{error}</p>}

      <button type="submit" className="hud-button btn-primary" disabled={loading}>
        {loading ? "Generating…" : "Generate"}
      </button>
    </form>
  );
}

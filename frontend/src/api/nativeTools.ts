import type {
  NativeToolArtifact,
  NativeToolDefinition,
  NativeToolRunResult,
  SystemSettings,
} from "../lib/nativeToolTypes";
import { NATIVE_TOOLS_STATIC } from "../lib/nativeToolTypes";

const ALL_TOOL_IDS = NATIVE_TOOLS_STATIC.map((t) => t.toolId);

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as Record<string, unknown>;
    if (typeof body.detail === "string") return body.detail;
    if (typeof body.error === "string") return body.error;
    return `请求失败（HTTP ${res.status}）`;
  } catch {
    return res.statusText || `请求失败（HTTP ${res.status}）`;
  }
}

export async function fetchNativeTools(): Promise<NativeToolDefinition[]> {
  try {
    const res = await fetch(apiUrl("/api/tools"));
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  } catch {
    return NATIVE_TOOLS_STATIC;
  }
}

export async function fetchNativeToolArtifacts(): Promise<NativeToolArtifact[]> {
  try {
    const res = await fetch(apiUrl("/api/tools/artifacts"));
    if (!res.ok) return [];
    const data = (await res.json()) as { artifacts: NativeToolArtifact[] };
    return data.artifacts ?? [];
  } catch {
    return [];
  }
}

export async function fetchNativeArtifactContent(
  jobId: string,
  filename: string,
): Promise<{ content: string; contentType: string }> {
  const res = await fetch(apiUrl(`/api/tools/artifacts/${encodeURIComponent(jobId)}/${filename}`));
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return { content: data.content, contentType: data.contentType };
}

export async function convertMarkdown(form: FormData): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/markdown/convert"), { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function scanFolder(body: {
  target_path: string;
  scan_mode: string;
  dry_run: boolean;
  max_depth: number;
}): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/folder-clean/scan"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function generateGitHubResume(body: {
  repo_url: string;
  language: string;
  role_target: string;
}): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/github-resume/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function queryRagStub(body: {
  document_path: string;
  question: string;
  top_k: number;
  model: string;
}): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/rag/query"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function downloadBilibiliStub(body: {
  url: string;
  output_dir: string;
  quality: string;
}): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/bilibili/download"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function runQuickForgeStub(body: {
  script: string;
  args: string[];
}): Promise<NativeToolRunResult> {
  const res = await fetch(apiUrl("/api/tools/quickforge/run"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchSystemSettings(): Promise<SystemSettings> {
  try {
    const res = await fetch(apiUrl("/api/settings"));
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  } catch {
    return {
      model: { provider: "demo", modelName: "demo", apiKeyConfigured: false, demoMode: true },
      storage: { workspaceRoot: "workspace", artifactRoot: "tool_artifacts", maxArtifactSizeMb: 50 },
      tool: {
        enabledTools: ALL_TOOL_IDS,
        defaultOutputDirectory: "tool_output",
        dryRunDefault: true,
      },
      runtime: {
        maxIterations: 8,
        plannerTimeoutSeconds: 20,
        toolTimeoutSeconds: 30,
        statusPollingIntervalMs: 2000,
      },
    };
  }
}

export async function saveSystemSettings(patch: Partial<SystemSettings>): Promise<SystemSettings> {
  const res = await fetch(apiUrl("/api/settings"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

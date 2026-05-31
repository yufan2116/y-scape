import type { ToolIntegrationConfig, ToolStatus } from "../lib/toolTypes";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as Record<string, unknown>;
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    return `请求失败（HTTP ${res.status}）`;
  } catch {
    return res.statusText || `请求失败（HTTP ${res.status}）`;
  }
}

export interface ToolPathConfig extends ToolIntegrationConfig {
  status?: ToolStatus;
  statusMessage?: string | null;
}

export async function fetchToolPaths(): Promise<ToolPathConfig[]> {
  const res = await fetch(apiUrl("/api/settings/tool-paths"));
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as { tools: ToolPathConfig[] };
  return data.tools;
}

export async function saveToolPath(config: Partial<ToolIntegrationConfig> & { tool_id: string }): Promise<ToolPathConfig> {
  const res = await fetch(apiUrl("/api/settings/tool-paths"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool: config }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as { tools: ToolPathConfig[] };
  return data.tools[0];
}

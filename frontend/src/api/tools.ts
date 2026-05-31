import type { ToolCategory, ToolIntegration, ToolRunResult, ToolStatus } from "../lib/toolTypes";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as Record<string, unknown>;
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join("；");
    }
    return `请求失败（HTTP ${res.status}）`;
  } catch {
    return res.statusText || `请求失败（HTTP ${res.status}）`;
  }
}

export async function fetchTools(): Promise<ToolIntegration[]> {
  const res = await fetch(apiUrl("/api/tools"));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchTool(toolId: string): Promise<ToolIntegration> {
  const res = await fetch(apiUrl(`/api/tools/${encodeURIComponent(toolId)}`));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function healthCheckTool(toolId: string): Promise<{
  toolId: string;
  status: ToolStatus;
  message?: string | null;
  configValid?: boolean;
  configError?: string | null;
}> {
  const res = await fetch(apiUrl(`/api/tools/${encodeURIComponent(toolId)}/health-check`), {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function runTool(
  toolId: string,
  input: Record<string, unknown> = {},
  dryRun = true,
): Promise<ToolRunResult> {
  const res = await fetch(apiUrl(`/api/tools/${encodeURIComponent(toolId)}/run`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input, dry_run: dryRun }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export const TOOL_CATEGORIES: { id: ToolCategory; label: string }[] = [
  { id: "Automation", label: "Automation" },
  { id: "Research", label: "Research" },
  { id: "Portfolio", label: "Portfolio" },
  { id: "Media", label: "Media" },
];

export function statusBadgeClass(status: ToolStatus): string {
  switch (status) {
    case "ready":
      return "tool-status-badge tool-status-badge--ready";
    case "error":
      return "tool-status-badge tool-status-badge--error";
    default:
      return "tool-status-badge tool-status-badge--pending";
  }
}

export function statusLabel(status: ToolStatus): string {
  switch (status) {
    case "ready":
      return "Ready";
    case "error":
      return "Error";
    default:
      return "Not configured";
  }
}

import { ALL_SSE_EVENT_TYPES, type RunEvent } from "../lib/runEvents";
import type {
  ArtifactPreviewResponse,
  CreateTaskResponse,
  DemoScenario,
  RunStatusSnapshot,
} from "../lib/taskTypes";

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
      return detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("；");
    }
    if (detail && typeof detail === "object") {
      const msg = (detail as { message?: unknown }).message;
      if (typeof msg === "string") return msg;
      return JSON.stringify(detail);
    }
    if (typeof body.message === "string") return body.message;
    return `请求失败（HTTP ${res.status}）`;
  } catch {
    return res.statusText || `请求失败（HTTP ${res.status}）`;
  }
}

export async function fetchDemoScenarios(): Promise<DemoScenario[]> {
  const res = await fetch(apiUrl("/api/demo/scenarios"));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createDemoTask(scenario: string, goal?: string): Promise<CreateTaskResponse> {
  const res = await fetch(apiUrl("/api/tasks/demo"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, goal: goal || undefined }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function startTask(runId: string): Promise<CreateTaskResponse> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/start`), { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchStatus(runId: string): Promise<RunStatusSnapshot> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/status`));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchEvents(runId: string, afterEventId?: string): Promise<RunEvent[]> {
  const q = afterEventId ? `?after_event_id=${encodeURIComponent(afterEventId)}` : "";
  const res = await fetch(apiUrl(`/api/tasks/${runId}/events${q}`));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchArtifactPreview(
  runId: string,
  filename: string,
): Promise<ArtifactPreviewResponse> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/artifacts/${encodeURIComponent(filename)}`));
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function cancelTask(runId: string): Promise<RunStatusSnapshot> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/cancel`), { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.status as RunStatusSnapshot;
}

export async function retryTask(runId: string): Promise<RunStatusSnapshot> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/retry`), { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.status as RunStatusSnapshot;
}

export async function resumeTask(runId: string): Promise<RunStatusSnapshot> {
  const res = await fetch(apiUrl(`/api/tasks/${runId}/resume`), { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.status as RunStatusSnapshot;
}

export function auditLogUrl(runId: string): string {
  return apiUrl(`/api/tasks/${runId}/audit-log`);
}

export function walUrl(runId: string): string {
  return apiUrl(`/api/tasks/${runId}/wal`);
}

export function replayUrl(runId: string): string {
  return apiUrl(`/api/tasks/${runId}/replay`);
}

function parseRunEvent(data: string): RunEvent | null {
  try {
    return JSON.parse(data) as RunEvent;
  } catch {
    return null;
  }
}

export type EventStreamCallbacks = {
  onEvent: (event: RunEvent) => void;
  onDone: () => void;
  onDisconnect: () => void;
  onConnect: () => void;
};

/** SSE with typed events; returns cleanup. */
export function subscribeEventStream(
  runId: string,
  callbacks: EventStreamCallbacks,
  lastEventId?: string,
): () => void {
  const url = new URL(apiUrl(`/api/tasks/${runId}/events/stream`), window.location.origin);
  if (lastEventId) {
    url.searchParams.set("last_event_id", lastEventId);
  }

  const source = new EventSource(url.toString());
  let closed = false;

  const handleData = (raw: string) => {
    const ev = parseRunEvent(raw);
    if (ev) callbacks.onEvent(ev);
  };

  source.onopen = () => {
    callbacks.onConnect();
  };

  for (const type of ALL_SSE_EVENT_TYPES) {
    source.addEventListener(type, (e: MessageEvent) => {
      if (e.data) handleData(e.data);
    });
  }

  source.addEventListener("done", () => {
    if (!closed) {
      closed = true;
      source.close();
      callbacks.onDone();
    }
  });

  source.onerror = () => {
    if (!closed) {
      source.close();
      callbacks.onDisconnect();
    }
  };

  return () => {
    closed = true;
    source.close();
  };
}

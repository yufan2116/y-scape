import type { RunState } from "./runState";

export interface ArtifactMeta {
  name: string;
  type: string;
  path: string;
  url: string;
  size: number;
  createdAt: string;
}

export interface RunStatusSnapshot {
  runId: string;
  goal: string;
  runState: RunState;
  runStateLabel: string;
  legacyStatus: string;
  currentStep?: string | null;
  currentTool?: string | null;
  thinkingMessage?: string | null;
  latestReasoning?: string | null;
  latestToolResult?: Record<string, unknown> | null;
  progress: number;
  artifacts: ArtifactMeta[];
  error?: string | null;
  stopReason?: string | null;
  revisionAttempt?: number;
  iteration?: number;
  demoMode?: boolean;
  taskType?: string;
  startedAt: string;
  updatedAt: string;
  finishedAt?: string | null;
  heartbeatAt: string;
  isStale: boolean;
  syncDelayed: boolean;
}

export interface CreateTaskResponse {
  runId: string;
  scenario?: string;
  status: RunStatusSnapshot;
}

export interface DemoScenario {
  name: string;
  goal: string;
  description: string;
  taskType: string;
}

export interface ArtifactPreviewResponse {
  name: string;
  content: string;
  contentType: string;
}

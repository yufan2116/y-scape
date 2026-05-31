export type ToolStatus = "ready" | "not_configured" | "error";

export type ToolCategory = "Automation" | "Research" | "Portfolio" | "Media";

export interface ToolIntegration {
  toolId: string;
  displayName: string;
  description: string;
  sourceProject: string;
  category: ToolCategory;
  status: ToolStatus;
  statusMessage?: string | null;
  inputSchema: Record<string, unknown>;
  inputSummary: string;
  lastRunAt?: string | null;
  enabled: boolean;
  timeoutSeconds: number;
  projectPath?: string;
  pythonExecutable?: string;
  entryScript?: string;
  workingDirectory?: string;
}

export interface ToolIntegrationConfig {
  tool_id: string;
  display_name: string;
  description: string;
  source_project: string;
  category: string;
  project_path: string;
  python_executable: string;
  entry_script: string;
  working_directory: string;
  enabled: boolean;
  timeout_seconds: number;
}

export interface ToolRunResult {
  ok: boolean;
  error?: string;
  status?: ToolStatus;
  dryRun?: boolean;
  message?: string;
  ranAt?: string;
  outputDir?: string;
  stdout?: string;
  stderr?: string;
}

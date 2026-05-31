export type NativeToolStatus = "available" | "stub" | "coming_soon";

export type NativeToolCategory =
  | "Research Tools"
  | "File Tools"
  | "Portfolio Tools"
  | "Media Tools"
  | "Automation Tools";

export interface NativeToolArtifact {
  name: string;
  type: string;
  url: string;
  size: number;
  jobId?: string;
  toolId?: string;
  createdAt?: string;
}

export interface NativeToolDefinition {
  toolId: string;
  name: string;
  category: NativeToolCategory;
  description: string;
  status: NativeToolStatus;
  inputSummary: string;
  recentArtifacts?: NativeToolArtifact[];
}

export interface NativeToolRunResult {
  ok: boolean;
  toolId: string;
  message?: string;
  error?: string;
  artifacts?: NativeToolArtifact[];
  data?: Record<string, unknown>;
}

export interface SystemSettings {
  model: {
    provider: string;
    modelName: string;
    apiKeyConfigured: boolean;
    demoMode: boolean;
  };
  storage: {
    workspaceRoot: string;
    artifactRoot: string;
    maxArtifactSizeMb: number;
  };
  tool: {
    enabledTools: string[];
    defaultOutputDirectory: string;
    dryRunDefault: boolean;
  };
  runtime: {
    maxIterations: number;
    plannerTimeoutSeconds: number;
    toolTimeoutSeconds: number;
    statusPollingIntervalMs: number;
  };
  advanced?: {
    externalIntegrationsEnabled?: boolean;
  };
}

export const NATIVE_TOOLS_STATIC: NativeToolDefinition[] = [
  {
    toolId: "markdown_convert",
    name: "Markdown Toolkit",
    category: "Research Tools",
    description: "PDF / DOCX / HTML / TXT 转 Markdown",
    status: "available",
    inputSummary: "Upload file · source type · output name",
  },
  {
    toolId: "folder_clean",
    name: "Folder Clean",
    category: "File Tools",
    description: "扫描文件夹 · 空目录 · 重复文件 · 大文件",
    status: "available",
    inputSummary: "Target path · scan mode · max depth",
  },
  {
    toolId: "github_resume_generator",
    name: "GitHub Resume Generator",
    category: "Portfolio Tools",
    description: "GitHub 仓库 → STAR 简历 bullet",
    status: "available",
    inputSummary: "Repo URL · language · role target",
  },
  {
    toolId: "local_rag_query",
    name: "Local RAG",
    category: "Research Tools",
    description: "本地文档索引与问答",
    status: "stub",
    inputSummary: "Document path · question · top_k",
  },
  {
    toolId: "bilibili_download",
    name: "Bilibili Download",
    category: "Media Tools",
    description: "B 站视频信息获取与下载",
    status: "stub",
    inputSummary: "URL / BV · output dir · quality",
  },
  {
    toolId: "quickforge_launcher",
    name: "QuickForge Launcher",
    category: "Automation Tools",
    description: "脚本管理与启动",
    status: "stub",
    inputSummary: "Script · args · run",
  },
];

export const NATIVE_TOOL_CATEGORIES: NativeToolCategory[] = [
  "Research Tools",
  "File Tools",
  "Portfolio Tools",
  "Media Tools",
  "Automation Tools",
];

export function nativeStatusLabel(status: NativeToolStatus): string {
  switch (status) {
    case "available":
      return "Available";
    case "stub":
      return "Stub";
    default:
      return "Coming Soon";
  }
}

export function nativeStatusClass(status: NativeToolStatus): string {
  switch (status) {
    case "available":
      return "native-tool-badge native-tool-badge--available";
    case "stub":
      return "native-tool-badge native-tool-badge--stub";
    default:
      return "native-tool-badge native-tool-badge--soon";
  }
}

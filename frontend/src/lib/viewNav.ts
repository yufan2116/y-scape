export type ActiveView =
  | "dashboard"
  | "missions"
  | "toolHub"
  | "artifacts"
  | "knowledgeBase"
  | "settings";

export interface NavItem {
  view: ActiveView;
  zh: string;
  en: string;
  icon: string;
}

export const NAV_ITEMS: NavItem[] = [
  { view: "dashboard", zh: "主控台", en: "Dashboard", icon: "◈" },
  { view: "missions", zh: "任务列表", en: "Missions", icon: "◎" },
  { view: "toolHub", zh: "工具中心", en: "Tool Hub", icon: "⬡" },
  { view: "artifacts", zh: "产物库", en: "Artifacts", icon: "▣" },
  { view: "knowledgeBase", zh: "知识库", en: "Knowledge Base", icon: "◫" },
  { view: "settings", zh: "系统设置", en: "Settings", icon: "⚙" },
];

export interface ViewMeta {
  zh: string;
  en: string;
  headline: string;
  description: string;
  hint?: string;
}

export const VIEW_META: Record<ActiveView, ViewMeta> = {
  dashboard: {
    zh: "主控台",
    en: "DASHBOARD",
    headline: "Mission Control",
    description: "当前任务运行面板",
  },
  missions: {
    zh: "任务列表",
    en: "MISSIONS",
    headline: "Mission History",
    description: "任务历史与 Mission 归档将在此显示。",
    hint: "支持查看过往 Run、状态筛选与快速恢复。",
  },
  toolHub: {
    zh: "工具中心",
    en: "TOOL HUB",
    headline: "Native Tool Modules",
    description: "系统内置工具 — 表单驱动，输出进入 Artifact 系统。",
    hint: "Research / File / Portfolio / Media / Automation",
  },
  artifacts: {
    zh: "产物库",
    en: "ARTIFACT LIBRARY",
    headline: "Deliverables Archive",
    description: "全局产物库将在此集中浏览与管理。",
    hint: "当前运行中的产物仍可在 Dashboard 右侧预览。",
  },
  knowledgeBase: {
    zh: "知识库",
    en: "KNOWLEDGE BASE",
    headline: "RAG Document Store",
    description: "Knowledge Base 将用于本地 RAG 文档管理。",
    hint: "支持上传文档、切片索引与检索调试。",
  },
  settings: {
    zh: "系统设置",
    en: "SETTINGS",
    headline: "System Configuration",
    description: "模型、存储、工具与 Runtime 全局配置。",
    hint: "外部项目路径配置已移至 Advanced（legacy integrations）。",
  },
};

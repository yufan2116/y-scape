import type { NativeToolDefinition } from "../../lib/nativeToolTypes";
import MarkdownConvertTool from "./MarkdownConvertTool";
import FolderCleanTool from "./FolderCleanTool";
import GitHubResumeTool from "./GitHubResumeTool";
import RagToolStub from "./RagToolStub";
import BilibiliToolStub from "./BilibiliToolStub";
import QuickForgeToolStub from "./QuickForgeToolStub";
import type { NativeToolRunResult } from "../../lib/nativeToolTypes";

interface Props {
  tool: NativeToolDefinition | null;
  onResult: (result: NativeToolRunResult) => void;
}

export default function ToolWorkspace({ tool, onResult }: Props) {
  if (!tool) {
    return (
      <div className="tool-workspace tool-workspace--empty">
        <p className="tool-workspace__hint">Select a tool from the left panel to begin.</p>
        <p className="muted">选择左侧工具卡片，在右侧工作区运行内置模块。</p>
      </div>
    );
  }

  return (
    <div className="tool-workspace">
      <header className="tool-workspace__head">
        <h3>{tool.name}</h3>
        <span className="tool-workspace__id">{tool.toolId}</span>
      </header>
      <p className="tool-workspace__desc">{tool.description}</p>

      {tool.toolId === "markdown_convert" && <MarkdownConvertTool onResult={onResult} />}
      {tool.toolId === "folder_clean" && <FolderCleanTool onResult={onResult} />}
      {tool.toolId === "github_resume_generator" && <GitHubResumeTool onResult={onResult} />}
      {tool.toolId === "local_rag_query" && <RagToolStub onResult={onResult} />}
      {tool.toolId === "bilibili_download" && <BilibiliToolStub onResult={onResult} />}
      {tool.toolId === "quickforge_launcher" && <QuickForgeToolStub onResult={onResult} />}
    </div>
  );
}

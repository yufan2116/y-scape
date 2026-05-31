import type { NativeToolDefinition } from "../../lib/nativeToolTypes";
import { nativeStatusClass, nativeStatusLabel } from "../../lib/nativeToolTypes";

interface Props {
  tool: NativeToolDefinition;
  active: boolean;
  onSelect: (toolId: string) => void;
}

export default function ToolCard({ tool, active, onSelect }: Props) {
  const recent = tool.recentArtifacts?.length ?? 0;

  return (
    <button
      type="button"
      className={`tool-card-native${active ? " tool-card-native--active" : ""}`}
      onClick={() => onSelect(tool.toolId)}
    >
      <div className="tool-card-native__head">
        <span className="tool-card-native__name">{tool.name}</span>
        <span className={nativeStatusClass(tool.status)}>{nativeStatusLabel(tool.status)}</span>
      </div>
      <span className="tool-card-native__cat">{tool.category}</span>
      <p className="tool-card-native__desc">{tool.description}</p>
      <p className="tool-card-native__meta">
        {recent > 0 ? `${recent} recent artifact(s)` : tool.inputSummary}
      </p>
    </button>
  );

}

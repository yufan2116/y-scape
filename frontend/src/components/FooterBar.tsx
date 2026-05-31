interface Props {
  sseConnected: boolean;
  usingEventPoll: boolean;
  heartbeatAt: string | null;
  runState: string | null;
  previewFilename?: string;
}

function fmtHeartbeat(iso: string | null): string {
  if (!iso) return "—";
  try {
    const sec = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (sec < 5) return "刚刚";
    return `${sec}s ago`;
  } catch {
    return iso;
  }
}

export default function FooterBar({
  sseConnected,
  usingEventPoll,
  heartbeatAt,
  runState,
  previewFilename,
}: Props) {
  const connLabel = sseConnected ? "Stable" : usingEventPoll ? "Polling" : "Waiting";
  const connZh = sseConnected ? "稳定" : usingEventPoll ? "轮询回退" : "等待连接";
  const workerActive =
    runState && !["success", "failed", "cancelled", "timeout", "idle"].includes(runState);

  const handleOpenEditor = () => {
    if (previewFilename) {
      window.open(`vscode://file/${previewFilename}`, "_blank");
    }
  };

  return (
    <footer className="aos-footer">
      <div className="aos-footer-items">
        <div className={`sr-footer-item ${sseConnected ? "ok" : usingEventPoll ? "warn" : ""}`}>
          <span className="sr-footer-dot" aria-hidden />
          <span>连接 · {connZh}</span>
          <span className="sr-footer-en">{connLabel}</span>
        </div>
        <div className={`sr-footer-item ${workerActive ? "ok" : ""}`}>
          <span className="sr-footer-icon" aria-hidden />
          <span>工作进程 · {workerActive ? "活跃" : "空闲"}</span>
          <span className="sr-footer-en">{workerActive ? "Active" : "Idle"}</span>
        </div>
        <div className="sr-footer-item">
          <span className="sr-footer-icon" aria-hidden />
          <span>心跳 · {fmtHeartbeat(heartbeatAt)}</span>
          <span className="sr-footer-en">Heartbeat</span>
        </div>
        <div className="sr-footer-item ok">
          <span className="sr-footer-icon" aria-hidden />
          <span>自动保存 · 已启用</span>
          <span className="sr-footer-en">Auto-save Enabled</span>
        </div>
      </div>

      <button
        type="button"
        className="aos-footer-action hud-button"
        disabled={!previewFilename}
        onClick={handleOpenEditor}
        title={previewFilename ? `打开 ${previewFilename}` : "请先选择产物文件"}
      >
        <span className="aos-star-icon">✦</span>
        在编辑器中打开
      </button>
    </footer>
  );
}

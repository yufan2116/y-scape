import { useCallback, useState } from "react";
import Sidebar from "./components/Sidebar";
import TaskHeader from "./components/TaskHeader";
import MissionObjectiveRow from "./components/MissionObjectiveRow";
import Timeline from "./components/Timeline";
import AgentThinking from "./components/AgentThinking";
import ArtifactEditor from "./components/ArtifactEditor";
import FooterBar from "./components/FooterBar";
import DebugPanel from "./components/DebugPanel";
import ViewPlaceholder from "./components/ViewPlaceholder";
import ToolHubView from "./views/ToolHubView";
import SettingsView from "./views/SettingsView";
import { useRunStore } from "./stores/useRunStore";
import type { ActiveView } from "./lib/viewNav";

export default function App() {
  const store = useRunStore();
  const [activeView, setActiveView] = useState<ActiveView>("dashboard");
  const handleNavigate = useCallback((view: ActiveView) => {
    console.log(`[NAVIGATE] activeView=${view}`);
    setActiveView(view);
  }, []);

  const isDashboard = activeView === "dashboard";

  return (
    <div className="app sr-app aos-app app-shell">
      <div className="aos-stars" aria-hidden />
      <div className="aos-grid-lines" aria-hidden />
      <div className="sr-bg-orbit sr-bg-orbit-1" aria-hidden />
      <div className="sr-bg-orbit sr-bg-orbit-2" aria-hidden />

      <div className="aos-shell">
        <Sidebar
          runId={store.runId}
          status={store.status}
          events={store.events}
          activeView={activeView}
          onNavigate={handleNavigate}
        />

        <div className={`aos-main${isDashboard ? "" : " aos-main-view aos-main-view--placeholder"}`}>
          <TaskHeader
            runId={store.runId}
            status={store.status}
            events={store.events}
            recoveryLoading={store.recoveryLoading}
            onCancel={() => void store.doCancel()}
            onRetry={() => void store.doRetry()}
            onResume={() => void store.doResume()}
            onStartNew={store.resetForNewMission}
          />

          {isDashboard ? (
            <>
              <MissionObjectiveRow
                status={store.status}
                runId={store.runId}
                starting={store.starting}
                restoring={store.restoring}
                error={store.error}
                onStart={(s, g) => void store.startMission(s, g)}
              />

              <main className="aos-workspace">
                <Timeline
                  events={store.events}
                  sseConnected={store.sseConnected}
                  usingEventPoll={store.usingEventPoll}
                  onReplay={store.runId ? () => void store.reloadEvents() : undefined}
                />

                <AgentThinking
                  message={store.status?.thinkingMessage}
                  latestReasoning={store.status?.latestReasoning}
                  currentStep={store.status?.currentStep}
                  events={store.events}
                  currentTool={store.status?.currentTool}
                  status={store.status}
                />

                <ArtifactEditor
                  artifacts={store.status?.artifacts ?? []}
                  onPreview={(n) => void store.loadPreview(n)}
                  selected={store.previewName}
                  previewLoading={store.previewLoading}
                  content={store.preview}
                  filename={store.previewName}
                  contentType={store.previewContentType}
                  previewError={store.previewError}
                />
              </main>

              <DebugPanel
                runId={store.runId}
                status={store.status}
                events={store.events}
                error={store.error}
              />
            </>
          ) : activeView === "toolHub" ? (
            <ToolHubView />
          ) : activeView === "settings" ? (
            <SettingsView />
          ) : (
            <ViewPlaceholder view={activeView} />
          )}

          <FooterBar
            sseConnected={store.sseConnected}
            usingEventPoll={store.usingEventPoll}
            heartbeatAt={store.status?.heartbeatAt ?? store.status?.updatedAt ?? null}
            runState={store.status?.runState ?? null}
            previewFilename={store.previewName}
          />
        </div>
      </div>
    </div>
  );
}

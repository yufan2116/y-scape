import type { RunStatusSnapshot } from "../lib/taskTypes";
import MissionObjectivePanel from "./MissionObjectivePanel";
import RunStatePanel from "./RunStatePanel";

interface Props {
  status: RunStatusSnapshot | null;
  runId: string | null;
  starting: boolean;
  restoring: boolean;
  error: string | null;
  onStart: (scenario: string, goal?: string) => void;
}

export default function MissionObjectiveRow({
  status,
  runId,
  starting,
  restoring,
  error,
  onStart,
}: Props) {
  return (
    <div className="sr-brief-row">
      <MissionObjectivePanel
        status={status}
        runId={runId}
        starting={starting}
        restoring={restoring}
        error={error}
        onStart={onStart}
      />
      <RunStatePanel status={status} />
    </div>
  );
}

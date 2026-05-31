import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelTask,
  createDemoTask,
  fetchArtifactPreview,
  fetchEvents,
  fetchStatus,
  resumeTask,
  retryTask,
  startTask,
  subscribeEventStream,
} from "../api/client";
import { formatUserError } from "../lib/display";
import type { RunEvent } from "../lib/runEvents";
import { isTerminal } from "../lib/runState";
import {
  clearSession,
  getSavedPreviewName,
  getSavedRunId,
  savePreviewName,
  saveRunId,
} from "../lib/session";
import type { RunStatusSnapshot } from "../lib/taskTypes";
import { withTimeout } from "../lib/withTimeout";

const STATUS_POLL_MS = 2000;
const EVENT_POLL_MS = 2500;
const START_TIMEOUT_MS = 45_000;
const PREVIEW_TIMEOUT_MS = 20_000;
const RESTORE_TIMEOUT_MS = 20_000;

function mergeEvents(prev: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const seen = new Set(prev.map((e) => e.eventId));
  const merged = [...prev];
  for (const ev of incoming) {
    if (!seen.has(ev.eventId)) {
      seen.add(ev.eventId);
      merged.push(ev);
    }
  }
  return merged;
}

function lastEventId(events: RunEvent[]): string | undefined {
  return events.length > 0 ? events[events.length - 1].eventId : undefined;
}

export function useRunStore() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<RunStatusSnapshot | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [preview, setPreview] = useState<string>("");
  const [previewName, setPreviewName] = useState<string>("");
  const [previewContentType, setPreviewContentType] = useState<string>("");
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [usingEventPoll, setUsingEventPoll] = useState(false);

  const eventsRef = useRef<RunEvent[]>([]);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const statusPollRef = useRef<number | null>(null);
  const eventPollRef = useRef<number | null>(null);
  const restoredRef = useRef(false);
  const previewTimerRef = useRef<number | null>(null);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  const refreshStatus = useCallback(async (id: string) => {
    const snap = await withTimeout(
      fetchStatus(id),
      PREVIEW_TIMEOUT_MS,
      "状态同步超时，将稍后重试",
    );
    setStatus(snap);
    return snap;
  }, []);

  const pollEvents = useCallback(async (id: string) => {
    const after = lastEventId(eventsRef.current);
    const batch = await fetchEvents(id, after);
    if (batch.length > 0) {
      setEvents((prev) => mergeEvents(prev, batch));
    }
  }, []);

  const stopStreams = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    if (statusPollRef.current) {
      window.clearInterval(statusPollRef.current);
      statusPollRef.current = null;
    }
    if (eventPollRef.current) {
      window.clearInterval(eventPollRef.current);
      eventPollRef.current = null;
    }
    if (previewTimerRef.current) {
      window.clearTimeout(previewTimerRef.current);
      previewTimerRef.current = null;
    }
    setSseConnected(false);
    setUsingEventPoll(false);
  }, []);

  const startStatusPoll = useCallback(
    (id: string) => {
      if (statusPollRef.current) return;
      statusPollRef.current = window.setInterval(() => {
        void refreshStatus(id)
          .then((snap) => {
            if (isTerminal(snap.runState)) {
              if (statusPollRef.current) {
                window.clearInterval(statusPollRef.current);
                statusPollRef.current = null;
              }
            }
          })
          .catch(() => undefined);
      }, STATUS_POLL_MS);
    },
    [refreshStatus],
  );

  const attachEventStream = useCallback(
    (id: string) => {
      unsubscribeRef.current?.();
      const after = lastEventId(eventsRef.current);

      unsubscribeRef.current = subscribeEventStream(
        id,
        {
          onConnect: () => {
            setSseConnected(true);
            setUsingEventPoll(false);
            if (eventPollRef.current) {
              window.clearInterval(eventPollRef.current);
              eventPollRef.current = null;
            }
          },
          onEvent: (ev) => {
            setEvents((prev) => mergeEvents(prev, [ev]));
          },
          onDone: () => {
            setSseConnected(false);
            void refreshStatus(id).catch(() => undefined);
          },
          onDisconnect: () => {
            setSseConnected(false);
            setUsingEventPoll(true);
            if (!eventPollRef.current) {
              eventPollRef.current = window.setInterval(() => {
                void pollEvents(id).catch(() => undefined);
              }, EVENT_POLL_MS);
            }
          },
        },
        after,
      );
    },
    [pollEvents, refreshStatus],
  );

  const loadPreviewInternal = useCallback(async (id: string, filename: string) => {
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewName(filename);

    if (previewTimerRef.current) {
      window.clearTimeout(previewTimerRef.current);
    }

    previewTimerRef.current = window.setTimeout(() => {
      setPreviewLoading(false);
      setPreviewError("预览加载超时，请重试");
    }, PREVIEW_TIMEOUT_MS + 500);

    try {
      const data = await withTimeout(
        fetchArtifactPreview(id, filename),
        PREVIEW_TIMEOUT_MS,
        "预览加载超时，请重试",
      );
      setPreview(data.content ?? "");
      setPreviewContentType(data.contentType ?? "text/plain");
      savePreviewName(filename);
    } catch (e) {
      setPreview("");
      setPreviewContentType("");
      setPreviewError(formatUserError(e));
    } finally {
      if (previewTimerRef.current) {
        window.clearTimeout(previewTimerRef.current);
        previewTimerRef.current = null;
      }
      setPreviewLoading(false);
    }
  }, []);

  const beginRun = useCallback(
    async (id: string, initialStatus: RunStatusSnapshot, opts?: { previewFile?: string | null }) => {
      stopStreams();
      setRunId(id);
      setStatus(initialStatus);
      saveRunId(id);
      setEvents([]);
      eventsRef.current = [];

      let backlog: RunEvent[] = [];
      try {
        backlog = await withTimeout(
          fetchEvents(id),
          RESTORE_TIMEOUT_MS,
          "事件加载超时",
        );
      } catch {
        /* status still valid; polling/SSE will backfill */
      }
      setEvents(backlog);
      eventsRef.current = backlog;

      attachEventStream(id);

      if (!isTerminal(initialStatus.runState)) {
        startStatusPoll(id);
      }

      const previewFile = opts?.previewFile ?? getSavedPreviewName();
      if (previewFile) {
        void loadPreviewInternal(id, previewFile);
      }
    },
    [attachEventStream, loadPreviewInternal, startStatusPoll, stopStreams],
  );

  const restoreSession = useCallback(async () => {
    const saved = getSavedRunId();
    if (!saved) return;

    setRestoring(true);
    setError(null);
    try {
      const snap = await withTimeout(
        fetchStatus(saved),
        RESTORE_TIMEOUT_MS,
        "会话恢复超时，请重新启动任务",
      );
      await beginRun(saved, snap, { previewFile: getSavedPreviewName() });
    } catch (e) {
      clearSession();
      setError(formatUserError(e));
    } finally {
      setRestoring(false);
    }
  }, [beginRun]);

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    void restoreSession();
  }, [restoreSession]);

  const startMission = useCallback(
    async (scenario: string, goal?: string) => {
      setStarting(true);
      setError(null);
      setPreview("");
      setPreviewName("");
      setPreviewContentType("");
      setPreviewError(null);
      try {
        const created = await withTimeout(
          createDemoTask(scenario, goal?.trim() || undefined),
          START_TIMEOUT_MS,
          "创建任务超时，请检查后端是否运行",
        );
        const started = await withTimeout(
          startTask(created.runId),
          START_TIMEOUT_MS,
          "启动任务超时，请重试",
        );
        await beginRun(created.runId, started.status);
      } catch (e) {
        setError(formatUserError(e));
      } finally {
        setStarting(false);
      }
    },
    [beginRun],
  );

  const resetForNewMission = useCallback(() => {
    stopStreams();
    clearSession();
    setRunId(null);
    setStatus(null);
    setEvents([]);
    eventsRef.current = [];
    setPreview("");
    setPreviewName("");
    setPreviewContentType("");
    setPreviewError(null);
    setError(null);
  }, [stopStreams]);

  useEffect(() => () => stopStreams(), [stopStreams]);

  const loadPreview = useCallback(
    async (filename: string) => {
      if (!runId) return;
      await loadPreviewInternal(runId, filename);
    },
    [runId, loadPreviewInternal],
  );

  const runRecovery = useCallback(
    async (action: "cancel" | "retry" | "resume") => {
      if (!runId) return;
      setRecoveryLoading(true);
      setError(null);
      try {
        let snap: RunStatusSnapshot;
        const op =
          action === "cancel"
            ? () => cancelTask(runId)
            : action === "retry"
              ? () => retryTask(runId)
              : () => resumeTask(runId);
        snap = await withTimeout(op(), START_TIMEOUT_MS, "恢复操作超时，请重试");

        setStatus(snap);
        if (action === "retry" || action === "resume") {
          attachEventStream(runId);
          if (!isTerminal(snap.runState)) {
            startStatusPoll(runId);
          }
        }
        if (action === "cancel") {
          await refreshStatus(runId);
        }
      } catch (e) {
        setError(formatUserError(e));
      } finally {
        setRecoveryLoading(false);
      }
    },
    [runId, attachEventStream, refreshStatus, startStatusPoll],
  );

  const reloadEvents = useCallback(async () => {
    if (!runId) return;
    try {
      const backlog = await withTimeout(
        fetchEvents(runId),
        RESTORE_TIMEOUT_MS,
        "Timeline 重载超时",
      );
      setEvents(backlog);
      eventsRef.current = backlog;
    } catch (e) {
      setError(formatUserError(e));
    }
  }, [runId]);

  return {
    runId,
    status,
    events,
    preview,
    previewName,
    previewContentType,
    previewError,
    previewLoading,
    starting,
    recoveryLoading,
    restoring,
    error,
    sseConnected,
    usingEventPoll,
    startMission,
    resetForNewMission,
    loadPreview,
    doCancel: () => runRecovery("cancel"),
    doRetry: () => runRecovery("retry"),
    doResume: () => runRecovery("resume"),
    refreshStatus,
    reloadEvents,
  };
}

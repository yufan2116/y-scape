const RUN_KEY = "yscape_run_id";
const PREVIEW_KEY = "yscape_preview_name";

export function saveRunId(runId: string): void {
  try {
    localStorage.setItem(RUN_KEY, runId);
  } catch {
    /* quota / private mode */
  }
}

export function savePreviewName(name: string): void {
  try {
    localStorage.setItem(PREVIEW_KEY, name);
  } catch {
    /* ignore */
  }
}

export function getSavedRunId(): string | null {
  try {
    return localStorage.getItem(RUN_KEY);
  } catch {
    return null;
  }
}

export function getSavedPreviewName(): string | null {
  try {
    return localStorage.getItem(PREVIEW_KEY);
  } catch {
    return null;
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(RUN_KEY);
    localStorage.removeItem(PREVIEW_KEY);
  } catch {
    /* ignore */
  }
}

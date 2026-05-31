/** Safe display helpers — never render undefined/null/NaN/[object Object] in UI */

export function displayText(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "number") {
    if (Number.isNaN(value)) return fallback;
    return String(value);
  }
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : fallback;
  }
  return fallback;
}

export function displayPercent(progress: unknown, fallback = 0): number {
  if (typeof progress !== "number" || !Number.isFinite(progress)) return fallback;
  return Math.min(100, Math.max(0, Math.round(progress * 100)));
}

export function formatUserError(error: unknown): string {
  if (error instanceof Error) return error.message || "操作失败，请重试";
  if (typeof error === "string" && error.trim()) return error.trim();
  return "操作失败，请重试";
}

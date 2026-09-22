/**
 * Pure formatting helpers. The backend is the source of truth for every
 * number; these functions only format values for display.
 */

/** Format an integer with thousands separators. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

/**
 * Compact token formatting, e.g. `1.2M`, `845K`, `320`.
 * The backend returns raw integers; the UI displays compact forms.
 */
export function formatTokens(value: number): string {
  if (value >= 1_000_000_000) {
    return `${trimDecimal(value / 1_000_000_000)}B`;
  }
  if (value >= 1_000_000) {
    return `${trimDecimal(value / 1_000_000)}M`;
  }
  if (value >= 1_000) {
    return `${trimDecimal(value / 1_000)}K`;
  }
  return formatNumber(value);
}

function trimDecimal(value: number): string {
  return value >= 100
    ? String(Math.round(value))
    : value.toFixed(1).replace(/\.0$/, "");
}

/** Percent of an allowance used, clamped to 0–100. */
export function usagePercent(used: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((used / limit) * 100)));
}

/**
 * Relative time label such as "2 min ago", "1 hour ago", "3 days ago".
 * Falls back to a localised date for anything older than a week.
 */
export function formatRelativeTime(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;

  const seconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;

  return then.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** `2026-09-17T12:13:39Z` → `2026-09-17 12:13`. */
export function formatDateTime(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${then.getFullYear()}-${pad(then.getMonth() + 1)}-${pad(
    then.getDate(),
  )} ${pad(then.getHours())}:${pad(then.getMinutes())}`;
}

/** `2026-09-17T12:13:39Z` → `12:13`. */
export function formatTime(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(then.getHours())}:${pad(then.getMinutes())}`;
}

/**
 * Calendar grouping for conversation sidebars:
 * `Today`, `Yesterday`, then the weekday, falling back to the date.
 */
export function dayGroupLabel(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "Earlier";

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const dayMs = 24 * 60 * 60 * 1000;
  const diffDays = Math.round((startOfToday.getTime() - then.getTime()) / dayMs);

  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) {
    return then.toLocaleDateString(undefined, { weekday: "long" });
  }
  return then.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

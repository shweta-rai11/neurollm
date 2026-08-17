/** Shared formatting helpers used across feature panels and pages. */

/** Truncate a string to `max` chars, appending an ellipsis if it was cut. */
export function truncate(text: string, max = 100): string {
  if (!text) return ''
  const trimmed = text.trim()
  if (trimmed.length <= max) return trimmed
  return `${trimmed.slice(0, max).trimEnd()}…`
}

/** Format an ISO timestamp as a human-readable date/time string. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

/** Clamp a value into the 0-100 range and round to the nearest integer. */
export function clampPct(value: number): number {
  return Math.round(Math.max(0, Math.min(100, value)))
}

/** Format a 0-100 numeric signal as a percentage label, e.g. "81%". */
export function pct(value: number): string {
  return `${clampPct(value)}%`
}

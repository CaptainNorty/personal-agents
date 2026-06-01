/**
 * Hours + minutes until local midnight, formatted "Xh Ym".
 * Used by Home (Done state) and the Done screen to show when tomorrow's
 * unknowns unlock. Backend doesn't currently expose a real cutoff time, so
 * this is the best approximation.
 */
export function timeUntilMidnight(): string {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  const diffMs = midnight.getTime() - now.getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  const minutes = Math.floor((diffMs % 3_600_000) / 60_000);
  return `${hours}h ${minutes}m`;
}

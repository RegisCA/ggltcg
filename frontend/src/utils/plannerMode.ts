/**
 * Human-readable planner label. The AI player has a single architecture
 * (enum-based turn planning) — this only exists to label historical log rows
 * from before that collapse, whose turn_plan JSON carries the legacy
 * `planner` value or, older still, an `ai_version` integer.
 */
export function plannerModeLabel(planner?: string | null, aiVersion?: number | null): string {
  if (planner) return planner;
  if (aiVersion === 4) return 'dual';
  if (aiVersion !== null && aiVersion !== undefined && aiVersion >= 3) return 'single';
  return 'per-action';
}

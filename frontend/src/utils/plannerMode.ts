/**
 * Human-readable planner mode label. Prefers the authoritative planner_mode
 * ('single' | 'dual' | 'enum'); falls back to the legacy ai_version integer for
 * older logs that predate planner_mode (4 → dual, ≥3 → single, 2 → per-action).
 */
export function plannerModeLabel(plannerMode?: string | null, aiVersion?: number | null): string {
  if (plannerMode) return plannerMode;
  if (aiVersion === 4) return 'dual';
  if (aiVersion !== null && aiVersion !== undefined && aiVersion >= 3) return 'single';
  return 'per-action';
}

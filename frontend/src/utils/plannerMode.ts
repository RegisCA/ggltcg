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

/**
 * Player-facing nickname for the AI, shown on the victory screen. The raw
 * planner values ("enum", "dual", ...) are developer terminology; players see
 * a friendly persona instead, while keeping the "the AI changed" signal Régis
 * wants (a different persona means a different architecture). The admin data
 * viewer keeps using {@link plannerModeLabel} for the raw technical value.
 */
const PLANNER_NICKNAMES: Record<string, string> = {
  enum: 'Mastermind',
};

export function plannerDisplayName(planner?: string | null, aiVersion?: number | null): string {
  const raw = plannerModeLabel(planner, aiVersion);
  return PLANNER_NICKNAMES[raw] ?? raw;
}

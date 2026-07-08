/**
 * Pure helpers for the Admin Data Viewer.
 *
 * Moved verbatim out of AdminDataViewer.tsx as part of the tab split (PR A2)
 * — no logic changes, just exported at module scope.
 */

import { plannerModeLabel } from '../../utils/plannerMode';
import type { AILog, TurnCharge } from './types';

// Group AI logs by turn — every live log has a turn_plan (the AI player
// is always a planner now), so grouping no longer depends on ai_version.
export interface TurnGroup {
  key: string;
  game_id: string;
  turn_number: number;
  player_id: string;
  model_name: string;
  prompts_version: string;
  ai_version: number | null;
  planner: string | null;
  turn_plan: NonNullable<AILog['turn_plan']>;
  created_at: string;
  logs: AILog[];
  has_fallback: boolean;
  fallback_reason: string | null;
}

export const groupLogsByTurn = (logs: AILog[]): (TurnGroup | AILog)[] => {
  const planGroups = new Map<string, TurnGroup>();
  const legacyLogs: AILog[] = [];

  for (const log of logs) {
    // Group any log carrying a turn plan; logs without one predate planning.
    if (log.turn_plan) {
      const key = `${log.game_id}-${log.turn_number}-${log.player_id}`;
      if (!planGroups.has(key)) {
        planGroups.set(key, {
          key,
          game_id: log.game_id,
          turn_number: log.turn_number,
          player_id: log.player_id,
          model_name: log.model_name,
          prompts_version: log.prompts_version,
          ai_version: log.ai_version,
          planner: log.turn_plan?.planner ?? null,
          turn_plan: log.turn_plan,
          created_at: log.created_at,
          logs: [],
          has_fallback: false,
          fallback_reason: null,
        });
      }
      const group = planGroups.get(key)!;
      group.logs.push(log);
      if (log.plan_execution_status === 'fallback') {
        group.has_fallback = true;
        group.fallback_reason = log.fallback_reason;
      }
    } else {
      legacyLogs.push(log);
    }
  }

  // Combine and sort by created_at (most recent first)
  const result: (TurnGroup | AILog)[] = [...planGroups.values(), ...legacyLogs];
  result.sort((a, b) => {
    const aDate = 'logs' in a ? a.created_at : a.created_at;
    const bDate = 'logs' in b ? b.created_at : b.created_at;
    return new Date(bDate).getTime() - new Date(aDate).getTime();
  });

  return result;
};

export const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

export const formatDuration = (startDate: string, endDate: string | null) => {
  if (!endDate) return 'In progress';
  const start = new Date(startDate);
  const end = new Date(endDate);
  const durationMs = end.getTime() - start.getTime();
  const minutes = Math.floor(durationMs / 60000);
  const seconds = Math.floor((durationMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
};

export const formatRelativeTime = (dateString: string | null) => {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
};

// Symptom counting (simple substring counts for repeatability)
export const SYMPTOM_PATTERNS: Record<string, string> = {
  json_parse_error: 'JSON parse error',
  invalid_sequence_index: 'Invalid sequence index',
  invalid_action_number: 'Invalid action number',
  didnt_specify_target: "AI didn't specify target",
  ai_failed_to_select_action: 'AI failed to select action',
  plan_deviation: 'Plan deviation',
  charge_went_negative: 'Charge went negative',
  sequence_rejected: 'rejected:',
  v4_r2_parse_error_flag: '"request2_parse_error": true',
  v4_r2_invalid_index_flag: '"request2_invalid_index": true',
};

export const formatMaybeNumber = (n: number | null | undefined, digits: number): string =>
  typeof n === 'number' && Number.isFinite(n) ? n.toFixed(digits) : '—';

export const copyTextToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for non-secure contexts / older browsers
    try {
      const el = document.createElement('textarea');
      el.value = text;
      el.style.position = 'fixed';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      el.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(el);
      return ok;
    } catch {
      return false;
    }
  }
};

export const normalizeText = (text?: string | null): string => (text ?? '').trim();

export const buildTurnCopyBundle = (turnGroup: TurnGroup): string => {
  const lines: string[] = [];
  const tp = turnGroup.turn_plan;

  let wrotePromptBlock = false;
  const pushPromptBlock = (title: string, body: string) => {
    if (wrotePromptBlock) {
      lines.push('');
      lines.push('---');
      lines.push('');
    } else {
      lines.push('');
    }
    wrotePromptBlock = true;
    lines.push(`### ${title}`);
    lines.push('```text');
    lines.push(body);
    lines.push('```');
  };

  lines.push(`Game: ${turnGroup.game_id}`);
  lines.push(`Turn: ${turnGroup.turn_number}`);
  lines.push(`Player: ${turnGroup.player_id}`);
  lines.push(`Model: ${turnGroup.model_name}`);
  lines.push(`Planner: ${plannerModeLabel(turnGroup.planner, turnGroup.ai_version)}`);
  if (turnGroup.fallback_reason) lines.push(`Fallback: ${turnGroup.fallback_reason}`);
  lines.push('');

  if (tp?.strategy) {
    lines.push('=== Strategy ===');
    lines.push(String(tp.strategy));
    lines.push('');
  }

  if (tp?.enum_debug) {
    lines.push('=== Planner Diagnostics ===');
    lines.push(safeJsonString(tp.enum_debug));
    lines.push('');
  }

  const planningPrompt = tp?.planning_prompt;
  const planningResponse = tp?.planning_response;
  const selectionPrompt = tp?.selection_prompt;
  const selectionResponse = tp?.selection_response;

  const isSelectionPromptSameAsPlanning = normalizeText(planningPrompt) !== '' && normalizeText(planningPrompt) === normalizeText(selectionPrompt);
  const isSelectionResponseSameAsPlanning = normalizeText(planningResponse) !== '' && normalizeText(planningResponse) === normalizeText(selectionResponse);

  if (planningPrompt) {
    pushPromptBlock('Planning Prompt', String(planningPrompt));
  }
  if (planningResponse) {
    pushPromptBlock('Planning Response', String(planningResponse));
  }

  if (selectionPrompt && !isSelectionPromptSameAsPlanning) {
    pushPromptBlock('Strategic Selection Prompt', String(selectionPrompt));
  }
  if (selectionResponse && !isSelectionResponseSameAsPlanning) {
    pushPromptBlock('Strategic Selection Response', String(selectionResponse));
  }

  if (Array.isArray(tp?.action_sequence) && tp.action_sequence.length > 0) {
    lines.push('=== Planned Action Sequence ===');
    lines.push(safeJsonString(tp.action_sequence));
    lines.push('');
  }
  if (Array.isArray(tp?.execution_log) && tp.execution_log.length > 0) {
    lines.push('=== Execution Log ===');
    lines.push(safeJsonString(tp.execution_log));
    lines.push('');
  }

  if (turnGroup.logs && turnGroup.logs.length > 0) {
    lines.push('=== Raw AILog Entries ===');
    for (const log of turnGroup.logs) {
      lines.push(`--- log_id=${log.id} action_number=${log.action_number ?? '—'} created_at=${log.created_at} ---`);
      if (log.prompt) {
        lines.push('[prompt]');
        lines.push(log.prompt);
      }
      if (log.response) {
        lines.push('[response]');
        lines.push(log.response);
      }
      if (log.reasoning) {
        lines.push('[reasoning]');
        lines.push(log.reasoning);
      }
      if (log.fallback_reason) {
        lines.push('[fallback_reason]');
        lines.push(log.fallback_reason);
      }
      lines.push('');
    }
  }

  return lines.join('\n');
};

export const countSymptoms = (text: string): Record<string, number> => {
  const counts: Record<string, number> = {};
  for (const [key, substr] of Object.entries(SYMPTOM_PATTERNS)) {
    if (!substr) continue;
    counts[key] = text.split(substr).length - 1;
  }
  return counts;
};

export const mergeCounts = (a: Record<string, number>, b: Record<string, number>): Record<string, number> => {
  const merged: Record<string, number> = { ...a };
  for (const [k, v] of Object.entries(b)) {
    merged[k] = (merged[k] || 0) + (v || 0);
  }
  return merged;
};

export const totalCount = (counts: Record<string, number>): number =>
  Object.values(counts).reduce((sum, v) => sum + (v || 0), 0);

export const formatCountsInline = (counts: Record<string, number>): string => {
  const entries = Object.entries(counts)
    .filter(([, v]) => (v || 0) > 0)
    .sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return 'none';
  return entries.map(([k, v]) => `${k}: ${v}`).join(' · ');
};

export const safeJsonString = (value: unknown): string => {
  try {
    return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

export const buildTurnTextForSymptoms = (turnGroup: TurnGroup): string => {
  const parts: string[] = [];
  if (turnGroup.fallback_reason) parts.push(turnGroup.fallback_reason);

  const tp = turnGroup.turn_plan;
  if (tp) {
    const isSelectionPromptSameAsPlanning = normalizeText(tp.planning_prompt) !== '' && normalizeText(tp.planning_prompt) === normalizeText(tp.selection_prompt);
    const isSelectionResponseSameAsPlanning = normalizeText(tp.planning_response) !== '' && normalizeText(tp.planning_response) === normalizeText(tp.selection_response);

    if (tp.planning_prompt) parts.push(tp.planning_prompt);
    if (tp.planning_response) parts.push(tp.planning_response);
    if (tp.selection_prompt && !isSelectionPromptSameAsPlanning) parts.push(tp.selection_prompt);
    if (tp.selection_response && !isSelectionResponseSameAsPlanning) parts.push(tp.selection_response);
    if (tp.execution_log) {
      for (const e of tp.execution_log) {
        if (e.reason) parts.push(e.reason);
        if (e.planned_action) parts.push(e.planned_action);
      }
    }
    if (tp.action_sequence) {
      for (const a of tp.action_sequence) {
        if (a.reasoning) parts.push(a.reasoning);
      }
    }
    if (tp.enum_debug) parts.push(safeJsonString(tp.enum_debug));
  }

  for (const log of turnGroup.logs) {
    if (log.prompt) parts.push(log.prompt);
    if (log.response) parts.push(log.response);
    if (log.reasoning) parts.push(log.reasoning);
    if (log.fallback_reason) parts.push(log.fallback_reason);
  }

  return parts.filter(Boolean).join('\n');
};

export const buildLogTextForSymptoms = (log: AILog): string => {
  const parts: string[] = [];
  if (log.prompt) parts.push(log.prompt);
  if (log.response) parts.push(log.response);
  if (log.reasoning) parts.push(log.reasoning);
  if (log.fallback_reason) parts.push(log.fallback_reason);
  if (log.turn_plan) {
    parts.push(safeJsonString(log.turn_plan));
  }
  return parts.filter(Boolean).join('\n');
};

export const computeActiveTurnChargeAveragesFromPlayback = (
  chargeTracking: TurnCharge[] | null,
  player1Id: string,
  player2Id: string
): { p1_avg: number | null; p2_avg: number | null; p1_samples: number; p2_samples: number } => {
  if (!chargeTracking || chargeTracking.length === 0) return { p1_avg: null, p2_avg: null, p1_samples: 0, p2_samples: 0 };
  const p1 = chargeTracking.filter(r => r.player_id === player1Id);
  const p2 = chargeTracking.filter(r => r.player_id === player2Id);
  const avg = (rows: TurnCharge[]): number | null => {
    if (rows.length === 0) return null;
    return rows.reduce((s, r) => s + r.charge_end, 0) / rows.length;
  };
  return { p1_avg: avg(p1), p2_avg: avg(p2), p1_samples: p1.length, p2_samples: p2.length };
};

export const computeActiveTurnChargeAveragesFromSimulation = (
  chargeTracking: TurnCharge[]
): { p1_avg: number | null; p2_avg: number | null; p1_samples: number; p2_samples: number } => {
  if (!chargeTracking || chargeTracking.length === 0) return { p1_avg: null, p2_avg: null, p1_samples: 0, p2_samples: 0 };
  const isActive = (row: TurnCharge): boolean => {
    const expected = row.turn % 2 === 1 ? 'player1' : 'player2';
    return row.player_id === expected;
  };
  const activeRows = chargeTracking.filter(isActive);
  const p1 = activeRows.filter(r => r.player_id === 'player1');
  const p2 = activeRows.filter(r => r.player_id === 'player2');
  const avg = (rows: TurnCharge[]): number | null => {
    if (rows.length === 0) return null;
    return rows.reduce((s, r) => s + r.charge_end, 0) / rows.length;
  };
  return { p1_avg: avg(p1), p2_avg: avg(p2), p1_samples: p1.length, p2_samples: p2.length };
};

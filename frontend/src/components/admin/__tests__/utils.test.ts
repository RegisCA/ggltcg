/**
 * Unit tests for the admin pure helpers moved out of AdminDataViewer.tsx
 * (PR A2): turn grouping, symptom counting, formatters, and the
 * copy-bundle builder.
 */
import { describe, it, expect } from 'vitest';
import {
  groupLogsByTurn,
  formatDate,
  formatDuration,
  formatRelativeTime,
  countSymptoms,
  mergeCounts,
  totalCount,
  formatCountsInline,
  formatMaybeNumber,
  safeJsonString,
  buildTurnCopyBundle,
  buildTurnTextForSymptoms,
  computeActiveTurnChargeAveragesFromPlayback,
  computeActiveTurnChargeAveragesFromSimulation,
} from '../utils';
import type { TurnGroup } from '../utils';
import type { AILog, TurnCharge } from '../types';

const makeLog = (overrides: Partial<AILog> = {}): AILog => ({
  id: 1,
  game_id: 'game-a',
  turn_number: 1,
  player_id: 'player2',
  model_name: 'gemini-2.5-flash-lite',
  prompts_version: 'v1',
  prompt: '',
  response: '',
  action_number: 1,
  reasoning: null,
  created_at: '2026-07-01T10:00:00Z',
  ai_version: null,
  turn_plan: {
    planner: 'enum',
    strategy: 'Break the slats',
    total_actions: 2,
    current_action: 1,
    charge_start: 4,
    charge_after_plan: 0,
    expected_cards_broken: 1,
  },
  plan_execution_status: 'complete',
  fallback_reason: null,
  planned_action_index: 0,
  ...overrides,
});

describe('groupLogsByTurn', () => {
  it('groups logs with turn plans by game/turn/player', () => {
    const logs = [
      makeLog({ id: 1 }),
      makeLog({ id: 2, action_number: 2 }),
      makeLog({ id: 3, turn_number: 3 }),
    ];
    const result = groupLogsByTurn(logs);
    expect(result).toHaveLength(2);
    const groups = result.filter((r): r is TurnGroup => 'logs' in r);
    expect(groups).toHaveLength(2);
    const turn1 = groups.find(g => g.turn_number === 1)!;
    expect(turn1.logs).toHaveLength(2);
    expect(turn1.planner).toBe('enum');
  });

  it('keeps logs without a turn plan as ungrouped legacy entries', () => {
    const logs = [makeLog({ id: 1 }), makeLog({ id: 2, turn_plan: null })];
    const result = groupLogsByTurn(logs);
    expect(result).toHaveLength(2);
    expect(result.some(r => !('logs' in r))).toBe(true);
  });

  it('flags fallback status on the group', () => {
    const logs = [
      makeLog({ id: 1 }),
      makeLog({ id: 2, plan_execution_status: 'fallback', fallback_reason: 'Plan deviation' }),
    ];
    const [group] = groupLogsByTurn(logs) as TurnGroup[];
    expect(group.has_fallback).toBe(true);
    expect(group.fallback_reason).toBe('Plan deviation');
  });

  it('sorts results most recent first', () => {
    const logs = [
      makeLog({ id: 1, turn_number: 1, created_at: '2026-07-01T10:00:00Z' }),
      makeLog({ id: 2, turn_number: 3, created_at: '2026-07-01T11:00:00Z' }),
    ];
    const result = groupLogsByTurn(logs) as TurnGroup[];
    expect(result[0].turn_number).toBe(3);
    expect(result[1].turn_number).toBe(1);
  });
});

describe('symptom counting', () => {
  it('counts substring occurrences per symptom pattern', () => {
    const text = 'JSON parse error\nsomething\nJSON parse error\nPlan deviation';
    const counts = countSymptoms(text);
    expect(counts.json_parse_error).toBe(2);
    expect(counts.plan_deviation).toBe(1);
    expect(counts.charge_went_negative).toBe(0);
  });

  it('merges and totals counts', () => {
    const merged = mergeCounts({ a: 1, b: 2 }, { b: 3, c: 1 });
    expect(merged).toEqual({ a: 1, b: 5, c: 1 });
    expect(totalCount(merged)).toBe(7);
  });

  it('formats counts inline, sorted descending, or "none"', () => {
    expect(formatCountsInline({})).toBe('none');
    expect(formatCountsInline({ a: 0 })).toBe('none');
    expect(formatCountsInline({ a: 1, b: 3 })).toBe('b: 3 · a: 1');
  });

  it('builds turn symptom text from plan, execution log, and raw logs', () => {
    const [group] = groupLogsByTurn([
      makeLog({
        id: 1,
        response: 'JSON parse error',
        fallback_reason: 'Plan deviation',
        plan_execution_status: 'fallback',
      }),
    ]) as TurnGroup[];
    const text = buildTurnTextForSymptoms(group);
    expect(text).toContain('JSON parse error');
    expect(text).toContain('Plan deviation');
    // Strategy is displayed separately, not part of the symptom text
    expect(text).not.toContain('Break the slats');
  });
});

describe('formatters', () => {
  it('formatDuration renders minutes and seconds, or "In progress"', () => {
    expect(formatDuration('2026-07-01T10:00:00Z', '2026-07-01T10:02:30Z')).toBe('2m 30s');
    expect(formatDuration('2026-07-01T10:00:00Z', null)).toBe('In progress');
  });

  it('formatRelativeTime buckets by age', () => {
    expect(formatRelativeTime(null)).toBe('Never');
    expect(formatRelativeTime(new Date().toISOString())).toBe('Just now');
    expect(formatRelativeTime(new Date(Date.now() - 5 * 60000).toISOString())).toBe('5m ago');
    expect(formatRelativeTime(new Date(Date.now() - 3 * 3600000).toISOString())).toBe('3h ago');
    expect(formatRelativeTime(new Date(Date.now() - 2 * 86400000).toISOString())).toBe('2d ago');
    const old = new Date(Date.now() - 30 * 86400000).toISOString();
    expect(formatRelativeTime(old)).toBe(formatDate(old));
  });

  it('formatMaybeNumber renders fixed digits or an em dash', () => {
    expect(formatMaybeNumber(1.2345, 2)).toBe('1.23');
    expect(formatMaybeNumber(null, 2)).toBe('—');
    expect(formatMaybeNumber(undefined, 1)).toBe('—');
    expect(formatMaybeNumber(NaN, 1)).toBe('—');
  });

  it('safeJsonString passes strings through and pretty-prints objects', () => {
    expect(safeJsonString('hello')).toBe('hello');
    expect(safeJsonString({ a: 1 })).toBe('{\n  "a": 1\n}');
  });
});

describe('buildTurnCopyBundle', () => {
  it('includes header, strategy, and raw log entries', () => {
    const [group] = groupLogsByTurn([
      makeLog({ id: 7, prompt: 'the prompt', response: 'the response' }),
    ]) as TurnGroup[];
    const bundle = buildTurnCopyBundle(group);
    expect(bundle).toContain('Game: game-a');
    expect(bundle).toContain('Turn: 1');
    expect(bundle).toContain('Planner: enum');
    expect(bundle).toContain('=== Strategy ===');
    expect(bundle).toContain('Break the slats');
    expect(bundle).toContain('log_id=7');
    expect(bundle).toContain('[prompt]');
    expect(bundle).toContain('the prompt');
  });

  it('deduplicates selection prompt/response identical to planning', () => {
    const [group] = groupLogsByTurn([
      makeLog({
        id: 8,
        turn_plan: {
          planner: 'enum',
          strategy: 's',
          total_actions: 1,
          current_action: 1,
          charge_start: 4,
          charge_after_plan: 0,
          expected_cards_broken: 0,
          planning_prompt: 'same prompt',
          planning_response: 'same response',
          selection_prompt: 'same prompt',
          selection_response: 'same response',
        },
      }),
    ]) as TurnGroup[];
    const bundle = buildTurnCopyBundle(group);
    expect(bundle).toContain('### Planning Prompt');
    expect(bundle).not.toContain('### Strategic Selection Prompt');
    expect(bundle).not.toContain('### Strategic Selection Response');
  });
});

describe('charge averages', () => {
  const rows: TurnCharge[] = [
    { turn: 1, player_id: 'player1', charge_start: 2, charge_gained: 0, charge_spent: 2, charge_end: 0 },
    { turn: 2, player_id: 'player2', charge_start: 4, charge_gained: 0, charge_spent: 2, charge_end: 2 },
    { turn: 3, player_id: 'player1', charge_start: 4, charge_gained: 0, charge_spent: 0, charge_end: 4 },
    // Inactive-turn row for player2 (turn 3 is player1's turn)
    { turn: 3, player_id: 'player2', charge_start: 2, charge_gained: 0, charge_spent: 0, charge_end: 2 },
  ];

  it('averages by player id for playbacks (all rows)', () => {
    const result = computeActiveTurnChargeAveragesFromPlayback(rows, 'player1', 'player2');
    expect(result.p1_avg).toBe(2);
    expect(result.p1_samples).toBe(2);
    expect(result.p2_avg).toBe(2);
    expect(result.p2_samples).toBe(2);
    expect(computeActiveTurnChargeAveragesFromPlayback(null, 'a', 'b')).toEqual({
      p1_avg: null, p2_avg: null, p1_samples: 0, p2_samples: 0,
    });
  });

  it('filters to active turns via turn parity for simulations', () => {
    const result = computeActiveTurnChargeAveragesFromSimulation(rows);
    // player2's turn-3 row is inactive (odd turn = player1) and is excluded
    expect(result.p1_samples).toBe(2);
    expect(result.p2_samples).toBe(1);
    expect(result.p2_avg).toBe(2);
  });
});

/**
 * usePacedGameState tests.
 *
 * Uses fake timers to drive the internal setTimeout-based release loop
 * deterministically. Snapshots are built via `makeGameState`, following the
 * same minimal-GameState factory convention used in
 * `components/__tests__/VictoryScreen.test.tsx`.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePacedGameState } from '../usePacedGameState';
import type { GameState } from '../../types/game';

const HUMAN_ID = 'human-1';
const AI_ID = 'ai-1';

function makeGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: 'game-1',
    turn_number: 2,
    phase: 'Main',
    active_player_id: AI_ID,
    first_player_id: HUMAN_ID,
    players: {
      [HUMAN_ID]: { player_id: HUMAN_ID, name: 'You', charge: 1, hand_count: 0, hand: null, in_play: [], break_zone: [], direct_attacks_this_turn: 0 },
      [AI_ID]: { player_id: AI_ID, name: 'Gemiknight', charge: 0, hand_count: 0, hand: null, in_play: [], break_zone: [], direct_attacks_this_turn: 0 },
    },
    winner: null,
    is_game_over: false,
    play_by_play: [],
    ...overrides,
  };
}

describe('usePacedGameState', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('presents the first snapshot immediately regardless of whose turn it is', () => {
    const s1 = makeGameState({ active_player_id: AI_ID });
    const { result } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID),
      { initialProps: { gs: s1 } }
    );
    expect(result.current).toBe(s1);
  });

  it('pass-through mode: presents own-turn snapshots immediately', () => {
    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID),
      { initialProps: { gs: s1 } }
    );
    expect(result.current).toBe(s1);

    const s2 = makeGameState({ active_player_id: HUMAN_ID, turn_number: 2 });
    rerender({ gs: s2 });
    // No timer needed; it's the viewer's own turn.
    expect(result.current).toBe(s2);
  });

  it('paces three rapid opponent snapshots at the minimum interval', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );
    expect(result.current).toBe(s0);

    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    const s2 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 2 } } });
    const s3 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 3 } } });

    rerender({ gs: s1 });
    // s1 is queued, not presented yet — still showing s0.
    expect(result.current).toBe(s0);

    rerender({ gs: s2 });
    rerender({ gs: s3 });

    // Nothing released before the interval elapses.
    act(() => { vi.advanceTimersByTime(799); });
    expect(result.current).toBe(s0);

    // First release lands right at the interval.
    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe(s1);

    act(() => { vi.advanceTimersByTime(800); });
    expect(result.current).toBe(s2);

    act(() => { vi.advanceTimersByTime(800); });
    expect(result.current).toBe(s3);
  });

  it('presents an opponent snapshot immediately when the interval already elapsed since the last present', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );
    expect(result.current).toBe(s0);

    // Let more than the interval pass with nothing queued (normal polling
    // spacing), then deliver a new opponent snapshot: no added latency.
    act(() => { vi.advanceTimersByTime(900); });
    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    rerender({ gs: s1 });
    expect(result.current).toBe(s1);
  });

  it('waits only the remaining interval for a snapshot arriving mid-interval', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    // Snapshot arrives 200ms after the last present: it should wait the
    // remaining 600ms, not a fresh 800ms.
    act(() => { vi.advanceTimersByTime(200); });
    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    rerender({ gs: s1 });
    expect(result.current).toBe(s0);

    act(() => { vi.advanceTimersByTime(599); });
    expect(result.current).toBe(s0);

    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe(s1);
  });

  it('ignores duplicate snapshots without resetting the pacing timer', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    rerender({ gs: s1 });
    expect(result.current).toBe(s0);

    // Advance partway, then feed an identical-content duplicate (new object,
    // same data) — this must not push the release further out.
    act(() => { vi.advanceTimersByTime(500); });
    const s1Duplicate = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    rerender({ gs: s1Duplicate });

    act(() => { vi.advanceTimersByTime(300); });
    expect(result.current).toBe(s1);
  });

  it('flushes remaining queue at the accelerated interval on turn handoff', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    // s2 hands the turn back to the viewer.
    const s2 = makeGameState({ active_player_id: HUMAN_ID, turn_number: 2 });

    rerender({ gs: s1 });
    rerender({ gs: s2 });
    expect(result.current).toBe(s0);

    // s1 releases at the normal interval.
    act(() => { vi.advanceTimersByTime(800); });
    expect(result.current).toBe(s1);

    // s2 (handoff) should flush at the accelerated 150ms interval, not 800ms.
    act(() => { vi.advanceTimersByTime(150); });
    expect(result.current).toBe(s2);
  });

  it('flushes immediately to the final snapshot on game over, skipping intermediates', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    const sGameOver = makeGameState({ active_player_id: AI_ID, turn_number: 1, is_game_over: true, winner: AI_ID });

    rerender({ gs: s1 });
    // Game-over arrives before s1 has been presented.
    rerender({ gs: sGameOver });

    // Should present the final (game-over) state immediately — no waiting.
    expect(result.current).toBe(sGameOver);
  });

  it('skips to the newest snapshot when the queue exceeds the staleness threshold', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { result, rerender } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    const snapshots = Array.from({ length: 7 }, (_, i) =>
      makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: i + 1 } } })
    );

    for (const s of snapshots) {
      rerender({ gs: s });
    }

    // The 6th push (queue length 6, exceeding MAX_QUEUE_SIZE=5) triggers an
    // immediate skip-ahead to the newest queued snapshot at that point.
    expect(result.current).toBe(snapshots[5]);

    // The 7th snapshot arrives after the guard already cleared the queue,
    // so it's queued fresh and released on the next normal-pace tick.
    act(() => { vi.advanceTimersByTime(800); });
    expect(result.current).toBe(snapshots[6]);
  });

  it('cleans up its pending timer on unmount', () => {
    const s0 = makeGameState({ active_player_id: AI_ID, turn_number: 1 });
    const { rerender, unmount } = renderHook(
      ({ gs }) => usePacedGameState(gs, HUMAN_ID, { minIntervalMs: 800 }),
      { initialProps: { gs: s0 } }
    );

    const s1 = makeGameState({ active_player_id: AI_ID, turn_number: 1, players: { ...s0.players, [AI_ID]: { ...s0.players[AI_ID], charge: 1 } } });
    rerender({ gs: s1 });

    const clearSpy = vi.spyOn(globalThis, 'clearTimeout');
    unmount();
    expect(clearSpy).toHaveBeenCalled();
    clearSpy.mockRestore();
  });
});

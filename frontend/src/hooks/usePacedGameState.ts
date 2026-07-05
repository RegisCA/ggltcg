/**
 * usePacedGameState
 *
 * The AI opponent executes one action per HTTP request, and GameBoard polls
 * game state every 2s. Plan-cached AI actions can resolve in well under a
 * second locally, so several distinct snapshots can arrive across polls
 * faster than a human can read them (and in human-vs-human games, several
 * opponent actions can collapse into a single poll). This hook is a pure
 * presentation buffer: it paces which snapshot is *rendered* during the
 * opponent's turn, without touching fetching/refetching at all.
 *
 * Modes:
 * - Pass-through: the viewer's own turn must feel instant, so any snapshot
 *   where the (about-to-be-presented) active player is the viewer is
 *   presented immediately and the queue is flushed. Game-over snapshots
 *   also flush immediately (never delay the victory screen). The very
 *   first snapshot (no presented state yet) is also pass-through.
 * - Paced: on the opponent's turn, snapshots are queued and released no
 *   sooner than `minIntervalMs` apart.
 * - Turn-handoff flush: if a still-queued snapshot turns out to no longer
 *   be the opponent's turn (viewer's turn now, or game over), we don't
 *   silently drop the intermediate snapshots the viewer hasn't seen yet.
 *   Non-game-over handoffs drain the remaining queue at an accelerated
 *   interval (150ms) so the tail of the opponent's turn is still visible,
 *   just quickly. Game-over handoffs skip straight to the final snapshot.
 * - Staleness guard: if polling piles up while backgrounded and the queue
 *   exceeds 5 entries, skip straight to the newest queued snapshot.
 *
 * Identity/dedup: `diffGameStates` (existing pure differ) is used to check
 * whether an incoming snapshot is semantically identical to the newest
 * queued/presented snapshot. Polling returns identical snapshots most of
 * the time, and those must not reset pacing timers or pile up the queue.
 */
import { useEffect, useRef, useState } from 'react';
import type { GameState } from '../types/game';
import { diffGameStates } from '../game/stateDiff';

const DEFAULT_MIN_INTERVAL_MS = 800;
const HANDOFF_FLUSH_INTERVAL_MS = 150;
const MAX_QUEUE_SIZE = 5;

function isPassThrough(state: GameState, viewerPlayerId: string): boolean {
  return (
    state.active_player_id === viewerPlayerId ||
    state.is_game_over ||
    !!state.winner
  );
}

function isSameState(a: GameState, b: GameState): boolean {
  return diffGameStates(a, b).length === 0;
}

export function usePacedGameState(
  gameState: GameState | undefined,
  viewerPlayerId: string,
  options?: { minIntervalMs?: number }
): GameState | undefined {
  const minIntervalMs = options?.minIntervalMs ?? DEFAULT_MIN_INTERVAL_MS;

  const [presented, setPresented] = useState<GameState | undefined>(undefined);

  // Queue of not-yet-presented snapshots, oldest first.
  const queueRef = useRef<GameState[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const presentedRef = useRef<GameState | undefined>(undefined);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const present = (state: GameState) => {
    presentedRef.current = state;
    setPresented(state);
  };

  // Schedules the next release from the queue at `delayMs`. Recurses via
  // setTimeout (not setInterval) so each release re-evaluates mode/queue
  // state instead of firing on a fixed cadence.
  const scheduleRelease = (delayMs: number) => {
    clearTimer();
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      releaseNext();
    }, delayMs);
  };

  const releaseNext = () => {
    const queue = queueRef.current;
    if (queue.length === 0) return;

    // Staleness guard: too much backlog, skip straight to the newest entry.
    if (queue.length > MAX_QUEUE_SIZE) {
      const newest = queue[queue.length - 1];
      queueRef.current = [];
      present(newest);
      return;
    }

    // Game-over anywhere in the remaining queue: jump straight to the last
    // snapshot, skipping intermediates, so the victory screen is never
    // delayed.
    const gameOverIndex = queue.findIndex((s) => s.is_game_over || !!s.winner);
    if (gameOverIndex !== -1) {
      const final = queue[queue.length - 1];
      queueRef.current = [];
      present(final);
      return;
    }

    const next = queue[0];
    const rest = queue.slice(1);
    queueRef.current = rest;
    present(next);

    if (rest.length === 0) return;

    // Turn-handoff: if the next queued snapshot is no longer the
    // opponent's turn, drain the remaining queue quickly instead of at the
    // normal pace.
    const handoffPending = rest.some((s) => isPassThrough(s, viewerPlayerId));
    scheduleRelease(handoffPending ? HANDOFF_FLUSH_INTERVAL_MS : minIntervalMs);
  };

  useEffect(() => {
    if (!gameState) return;

    // First snapshot ever: present immediately, nothing to pace against.
    if (!presentedRef.current) {
      queueRef.current = [];
      present(gameState);
      return;
    }

    // Dedup against the newest known snapshot (queued tail, or presented
    // state if the queue is empty) so identical polls don't reset timers
    // or grow the queue.
    const newestKnown =
      queueRef.current.length > 0
        ? queueRef.current[queueRef.current.length - 1]
        : presentedRef.current;
    if (newestKnown && isSameState(newestKnown, gameState)) {
      return;
    }

    // Game-over always flushes immediately, even mid-paced-sequence, so the
    // victory screen is never delayed behind queued opponent snapshots.
    if (gameState.is_game_over || !!gameState.winner) {
      clearTimer();
      queueRef.current = [];
      present(gameState);
      return;
    }

    if (isPassThrough(gameState, viewerPlayerId) && queueRef.current.length === 0) {
      // Nothing paced in-flight: safe to present this own-turn snapshot
      // immediately.
      clearTimer();
      present(gameState);
      return;
    }

    // Paced mode (or a turn-handoff snapshot arriving while a paced
    // sequence is still draining): enqueue. If this snapshot is
    // pass-through, `releaseNext`'s handoff check will notice it in the
    // queue and accelerate the remaining drain — it is never dropped.
    queueRef.current = [...queueRef.current, gameState];

    if (queueRef.current.length > MAX_QUEUE_SIZE) {
      // Staleness guard: skip ahead immediately.
      clearTimer();
      releaseNext();
      return;
    }

    if (timerRef.current === null) {
      scheduleRelease(minIntervalMs);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameState, viewerPlayerId, minIntervalMs]);

  // Clean up any pending timer on unmount.
  useEffect(() => {
    return () => clearTimer();
  }, []);

  return presented;
}

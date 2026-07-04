/**
 * ActionBar Component
 *
 * Compact charge + End Turn bar docked at the hand — the player's own Charge
 * readout lives here, next to where play decisions actually happen
 * (UI_REFRESH_2026_06 WP-2 #2: players read Charge near the hand, not in the
 * top header).
 *
 * Replaces the old ActionPanel sidebar list: hand cards and glowing in-play
 * cards are the play surface (clicking them plays/tussles directly), so the
 * only action without a card equivalent is End Turn.
 *
 * Keeps ActionPanel's '0' keyboard shortcut and its inactivity blink
 * reminders on the End Turn button.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidAction } from '../types/game';

interface ActionBarProps {
  charge: number;
  /** All currently valid actions. The bar only renders End Turn, but takes
   *  the full list so the inactivity timer resets on ANY action the player
   *  takes (playing/tussling changes the list), matching the old
   *  ActionPanel's behavior — the end_turn entry alone can stay
   *  reference-identical across react-query refetches. */
  validActions: ValidAction[];
  onAction: (action: ValidAction) => void;
  isProcessing: boolean;
  isCompact?: boolean;
}

export function ActionBar({
  charge,
  validActions,
  onAction,
  isProcessing,
  isCompact = false,
}: ActionBarProps) {
  const [shouldBlink, setShouldBlink] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(Date.now());

  // undefined when it's not the player's turn
  const endTurnAction = validActions.find(a => a.action_type === 'end_turn');

  const canEndTurn = !!endTurnAction && !isProcessing;

  const handleEndTurn = useCallback(() => {
    if (endTurnAction && !isProcessing) {
      onAction(endTurnAction);
    }
  }, [endTurnAction, isProcessing, onAction]);

  // Keyboard shortcut: 0 ends the turn (as in the old ActionPanel)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === '0') {
        event.preventDefault();
        handleEndTurn();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleEndTurn]);

  // Reset the inactivity timer whenever the valid-action list changes
  // (indicates an action was taken or the turn changed)
  useEffect(() => {
    setLastActionTime(Date.now());
    setShouldBlink(false);
  }, [validActions]);

  // Inactivity reminders on the End Turn button (ported from ActionPanel)
  useEffect(() => {
    if (!endTurnAction) return;

    const intervals = [
      { delay: 10000, duration: 2000 },   // 10s: blink for 2s
      { delay: 20000, duration: 2000 },   // 20s: blink for 2s
      { delay: 60000, duration: 2000 },   // 1min: blink for 2s
      { delay: 300000, duration: 0 },     // 5min: stop
    ];

    const timers: ReturnType<typeof setTimeout>[] = [];

    intervals.forEach(({ delay, duration }) => {
      const timer = setTimeout(() => {
        if (duration > 0) {
          setShouldBlink(true);
          setTimeout(() => setShouldBlink(false), duration);
        } else {
          setShouldBlink(false);
        }
      }, delay);
      timers.push(timer);
    });

    return () => {
      timers.forEach(timer => clearTimeout(timer));
    };
  }, [lastActionTime, endTurnAction]);

  return (
    <div
      className="bg-game-card rounded border-2 border-game-accent flex items-center justify-between"
      style={{
        padding: isCompact
          ? 'var(--spacing-component-xs) var(--spacing-component-sm)'
          : 'var(--spacing-component-sm) var(--spacing-component-md)',
        gap: 'var(--spacing-component-sm)',
      }}
    >
      {/* Your Charge — the readout players actually use when deciding plays */}
      <div className="flex items-end leading-none" style={{ gap: 'var(--spacing-component-xs)' }}>
        <span className={`${isCompact ? 'text-xl' : 'text-2xl'} font-bold text-yellow-400`} aria-hidden="true">⚡</span>
        <span className={`${isCompact ? 'text-2xl' : 'text-3xl'} font-bold`} aria-label={`${charge} Charge available`}>
          {charge}
        </span>
        <span className={`${isCompact ? 'text-sm' : 'text-base'} text-gray-400`}>Charge</span>
      </div>

      <button
        onClick={handleEndTurn}
        disabled={!canEndTurn}
        className={`
          rounded transition-all border-2 text-white font-bold
          bg-amber-600 hover:bg-amber-700
          ${!canEndTurn ? 'opacity-40 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-95'}
          ${shouldBlink ? 'animate-blink ring-4 ring-yellow-400' : 'border-transparent'}
          focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:ring-offset-game-card
        `}
        style={{
          padding: isCompact
            ? 'var(--spacing-component-xs) var(--spacing-component-md)'
            : 'var(--spacing-component-sm) var(--spacing-component-lg)',
          fontSize: isCompact ? '0.875rem' : '1rem',
          minHeight: 'var(--size-touch-target-min)',
        }}
      >
        <span className="flex items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
          <span
            className="flex items-center justify-center bg-black/30 rounded font-mono font-bold flex-shrink-0"
            style={{
              width: isCompact ? '20px' : '24px',
              height: isCompact ? '20px' : '24px',
              fontSize: isCompact ? '10px' : '0.75rem',
            }}
            title="Keyboard shortcut: 0"
          >
            0
          </span>
          End Turn
        </span>
      </button>
    </div>
  );
}

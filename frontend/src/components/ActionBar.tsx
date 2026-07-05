/**
 * ActionBar — the turn bar (Paper & Ink §7.2), the single turn control (§3).
 *
 * Your turn: `--bar` background with a gold top border, "Your Turn · Turn N" in
 * gold + a gold End Turn button. Opponent's turn: same bar, purple accent —
 * a pulsing purple dot + "{Opponent}'s Turn · Turn N" + "waiting…", no button.
 *
 * Charge is no longer here — it lives in the score chips (§7.1). Kept from the
 * old bar: the '0' End Turn shortcut and the inactivity blink reminder.
 *
 * Values from the signed-off mockup (6a your-turn, 6b opponent-turn).
 */

import { useState, useEffect, useCallback } from 'react';
import type { ValidAction } from '../types/game';

interface ActionBarProps {
  /** All currently valid actions — the bar renders only End Turn but takes the
   *  full list so the inactivity timer resets on ANY action the player takes. */
  validActions: ValidAction[];
  onAction: (action: ValidAction) => void;
  isProcessing: boolean;
  isYourTurn: boolean;
  turnNumber: number;
  /** Opponent's name, shown in the passive strip on their turn. */
  opponentName: string;
}

export function ActionBar({
  validActions,
  onAction,
  isProcessing,
  isYourTurn,
  turnNumber,
  opponentName,
}: ActionBarProps) {
  const [shouldBlink, setShouldBlink] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(Date.now());

  const endTurnAction = validActions.find(a => a.action_type === 'end_turn');
  const canEndTurn = !!endTurnAction && !isProcessing;

  const handleEndTurn = useCallback(() => {
    if (endTurnAction && !isProcessing) onAction(endTurnAction);
  }, [endTurnAction, isProcessing, onAction]);

  // Keyboard shortcut: 0 ends the turn
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

  // Reset the inactivity timer whenever the valid-action list changes.
  useEffect(() => {
    setLastActionTime(Date.now());
    setShouldBlink(false);
  }, [validActions]);

  // Inactivity reminders on the End Turn button.
  useEffect(() => {
    if (!endTurnAction) return;
    const intervals = [
      { delay: 10000, duration: 2000 },
      { delay: 20000, duration: 2000 },
      { delay: 60000, duration: 2000 },
      { delay: 300000, duration: 0 },
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
    return () => timers.forEach(timer => clearTimeout(timer));
  }, [lastActionTime, endTurnAction]);

  return (
    <div
      style={{
        background: 'var(--bar)',
        borderTop: `1px solid ${isYourTurn ? 'rgba(242,193,78,.35)' : 'rgba(180,142,222,.3)'}`,
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        minHeight: 'var(--size-touch-target-min)',
      }}
    >
      {isYourTurn ? (
        <>
          <span style={{ color: 'var(--gold)', fontWeight: 900, fontSize: '13px', paddingLeft: '4px' }}>
            Your Turn · Turn {turnNumber}
          </span>
          <button
            onClick={handleEndTurn}
            disabled={!canEndTurn}
            className={shouldBlink ? 'animate-blink' : ''}
            style={{
              marginLeft: 'auto',
              background: 'var(--gold)',
              color: 'var(--desk-bottom)',
              fontWeight: 900,
              fontSize: '13px',
              padding: '9px 20px',
              borderRadius: '6px',
              border: 'none',
              boxShadow: '0 3px 0 rgba(0,0,0,.5)',
              cursor: canEndTurn ? 'pointer' : 'not-allowed',
              opacity: canEndTurn ? 1 : 0.5,
            }}
          >
            End Turn
          </button>
        </>
      ) : (
        <>
          <span
            style={{
              width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
              background: 'var(--them)', boxShadow: '0 0 8px rgba(180,142,222,.8)',
              animation: 'pulse 1.6s ease-in-out infinite',
            }}
          />
          <span style={{ color: 'var(--them)', fontWeight: 900, fontSize: '13px' }}>
            {opponentName}'s Turn · Turn {turnNumber}
          </span>
          <span style={{ marginLeft: 'auto', color: 'rgba(237,232,222,.35)', fontSize: '11px' }}>waiting…</span>
        </>
      )}
    </div>
  );
}

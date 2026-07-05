/**
 * WaitingStatus Component
 *
 * Displays the current waiting status message based on lobby phase.
 */

import type { LobbyPhase } from '../../hooks/useLobbyPolling';

interface WaitingStatusProps {
  phase: LobbyPhase;
  currentPlayerId: 'player1' | 'player2';
}

export function WaitingStatus({ phase, currentPlayerId }: WaitingStatusProps) {
  const otherPlayerLabel = currentPlayerId === 'player1' ? 'Player 2' : 'Player 1';

  return (
    <div className="text-center">
      {phase === 'waiting-for-player' && (
        <div>
          <div style={{ fontSize: 'clamp(18px, 3vw, 22px)', fontWeight: 900, color: 'var(--ink-text)', marginBottom: 'var(--spacing-component-sm)' }}>
            Waiting for player 2 to join...
          </div>
          <div style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>Share the game code above</div>
        </div>
      )}
      {phase === 'waiting-for-decks' && (
        <div>
          <div style={{ fontSize: 'clamp(18px, 3vw, 22px)', fontWeight: 900, color: 'var(--ink-text)', marginBottom: 'var(--spacing-component-sm)' }}>
            Waiting for {otherPlayerLabel} to select their deck...
          </div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--you)' }}>Your deck is ready!</div>
        </div>
      )}
      {phase === 'starting' && (
        <div>
          <div style={{ fontSize: 'clamp(18px, 3vw, 22px)', fontWeight: 900, color: 'var(--gold)', marginBottom: 'var(--spacing-component-sm)' }}>
            Starting game...
          </div>
          <div style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>Get ready to play!</div>
        </div>
      )}
    </div>
  );
}

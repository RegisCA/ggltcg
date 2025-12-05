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
        <div className="text-2xl text-gray-200 font-semibold">
          <div style={{ marginBottom: 'var(--spacing-component-sm)' }}>⏳ Waiting for player 2 to join...</div>
          <div className="text-lg text-gray-300">Share the game code above</div>
        </div>
      )}
      {phase === 'waiting-for-decks' && (
        <div className="text-2xl text-gray-200 font-semibold">
          <div style={{ marginBottom: 'var(--spacing-component-sm)' }}>⏳ Waiting for {otherPlayerLabel} to select their deck...</div>
          <div className="text-lg text-green-400">✅ Your deck is ready!</div>
        </div>
      )}
      {phase === 'starting' && (
        <div className="text-2xl text-game-highlight font-bold">
          <div style={{ marginBottom: 'var(--spacing-component-sm)' }}>🎮 Starting game...</div>
          <div className="text-lg text-gray-300">Get ready to play!</div>
        </div>
      )}
    </div>
  );
}

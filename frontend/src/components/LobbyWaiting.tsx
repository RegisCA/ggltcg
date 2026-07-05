/**
 * Lobby Waiting Component
 *
 * Waiting room showing game code, players, and deck selection status.
 * Restyled to the Paper & Ink language: desk gradient, Gochi Hand headers,
 * dark panels with gold hairline borders, gold primary buttons.
 */

import { useState } from 'react';
import { startLobbyGame } from '../api/gameService';
import { useLobbyPolling, type LobbyPhase } from '../hooks/useLobbyPolling';
import { DeckSelection } from './DeckSelection';
import {
  GameCodeDisplay,
  LobbyHeader,
  PlayersBanner,
  PlayersStatusCard,
  WaitingStatus,
} from './lobby';

interface LobbyWaitingProps {
  gameId: string;
  gameCode: string;
  actualPlayerId: string;  // Google ID for API calls
  currentPlayerId: 'player1' | 'player2';  // For display purposes only
  currentPlayerName: string;
  otherPlayerName: string | null;
  onGameStarted: (gameId: string, firstPlayerId: string) => void;
  onBack: () => void;
  /** Test/preview seam: when provided, forces the lobby's initial phase and
   *  disables status polling. Production callers never pass this — used by
   *  the /design.html harness fixture to show 'deck-selection',
   *  'waiting-for-decks', or 'starting' without a backend. */
  initialPhaseOverride?: LobbyPhase;
  /** Test/preview seam: when true, the current player's deck is treated as
   *  already submitted (mirrors what happens after handleDeckSelected
   *  succeeds) so the waiting-room ready state renders correctly. */
  currentPlayerReadyOverride?: boolean;
}

export function LobbyWaiting({
  gameId,
  gameCode,
  actualPlayerId,
  currentPlayerId,
  currentPlayerName,
  otherPlayerName: initialOtherPlayerName,
  onGameStarted,
  onBack,
  initialPhaseOverride,
  currentPlayerReadyOverride,
}: LobbyWaitingProps) {
  const [currentPlayerReady, setCurrentPlayerReady] = useState(currentPlayerReadyOverride ?? false);
  const [error, setError] = useState<string | null>(null);

  // Use polling hook for lobby status
  const { phase, otherPlayerName, otherPlayerReady, setPhase } = useLobbyPolling({
    gameCode,
    initialOtherPlayerName,
    onGameReady: () => onGameStarted(gameId, ''),
    disablePolling: initialPhaseOverride !== undefined,
  });

  const effectivePhase = initialPhaseOverride ?? phase;

  // Handle deck selection submission
  const handleDeckSelected = async (deck: string[]) => {
    setError(null);

    try {
      const response = await startLobbyGame(gameCode, {
        player_id: actualPlayerId,  // Use actual Google ID
        deck,
      });

      setCurrentPlayerReady(true);

      // Check if game is ready to start (both players submitted)
      if (response.status === 'active' && response.first_player_id) {
        onGameStarted(gameId, response.first_player_id);
      } else {
        setPhase('waiting-for-decks');
      }
    } catch (err: unknown) {
      console.error('Failed to submit deck:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any).response?.data?.detail || 'Failed to submit deck. Please try again.');
    }
  };

  // Get player names for display
  const player1Name = currentPlayerId === 'player1' ? currentPlayerName : otherPlayerName || '';
  const player2Name = currentPlayerId === 'player2' ? currentPlayerName : otherPlayerName || '';

  // Deck selection phase
  if (effectivePhase === 'deck-selection' && !currentPlayerReady) {
    return (
      <div style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))', color: 'var(--ink-text)', minHeight: '100vh' }}>
        <LobbyHeader gameCode={gameCode} onBack={onBack} />

        <PlayersBanner
          player1Name={player1Name}
          player2Name={player2Name}
          currentPlayerId={currentPlayerId}
        />

        {error && (
          <div
            className="max-w-2xl mx-auto"
            style={{
              background: 'rgba(224,113,107,.12)',
              border: '1px solid var(--danger)',
              borderRadius: '6px',
              padding: 'var(--spacing-component-md)',
              marginTop: 'var(--spacing-component-md)',
            }}
          >
            <div style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '13px' }}>{error}</div>
          </div>
        )}

        <DeckSelection
          onDeckSelected={handleDeckSelected}
        />
      </div>
    );
  }

  // Waiting room display (waiting for player, waiting for decks, starting)
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        padding: 'var(--spacing-component-md)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      <div className="max-w-2xl w-full">
        {/* Back Button */}
        <div style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <button
            onClick={onBack}
            className="flex items-center transition-colors"
            style={{
              gap: 'var(--spacing-component-xs)',
              color: 'var(--ink-muted)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '13px',
            }}
          >
            <span>←</span> Back to Main Menu
          </button>
        </div>

        {/* Game Code Display */}
        <div
          style={{
            background: '#241E17',
            borderRadius: '8px',
            border: '1px solid rgba(242,193,78,.25)',
            padding: 'var(--spacing-component-xl)',
            marginBottom: 'var(--spacing-component-lg)',
          }}
        >
          <GameCodeDisplay
            code={gameCode}
            size="large"
            label="Share this code with your friend:"
          />
        </div>

        {/* Players Status */}
        <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
          <PlayersStatusCard
            player1={{
              name: player1Name || null,
              isCurrentPlayer: currentPlayerId === 'player1',
              isReady: currentPlayerId === 'player1' ? currentPlayerReady : otherPlayerReady,
            }}
            player2={{
              name: player2Name || null,
              isCurrentPlayer: currentPlayerId === 'player2',
              isReady: currentPlayerId === 'player2' ? currentPlayerReady : otherPlayerReady,
            }}
          />
        </div>

        {/* Status Message */}
        <WaitingStatus phase={effectivePhase} currentPlayerId={currentPlayerId} />
      </div>
    </div>
  );
}

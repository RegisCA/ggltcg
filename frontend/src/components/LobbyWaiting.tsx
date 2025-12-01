/**
 * Lobby Waiting Component
 * 
 * Waiting room showing game code, players, and deck selection status.
 * Refactored to use shared hooks and components.
 */

import { useState } from 'react';
import { startLobbyGame } from '../api/gameService';
import { useLobbyPolling } from '../hooks/useLobbyPolling';
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
}: LobbyWaitingProps) {
  const [currentPlayerReady, setCurrentPlayerReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use polling hook for lobby status
  const { phase, otherPlayerName, otherPlayerReady, setPhase } = useLobbyPolling({
    gameCode,
    initialOtherPlayerName,
    onGameReady: () => onGameStarted(gameId, ''),
  });

  // Handle deck selection submission
  const handleDeckSelected = async (deck: string[], _playerName: string) => {
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
    } catch (err: any) {
      console.error('Failed to submit deck:', err);
      setError(err.response?.data?.detail || 'Failed to submit deck. Please try again.');
    }
  };

  // Get player names for display
  const player1Name = currentPlayerId === 'player1' ? currentPlayerName : otherPlayerName || '';
  const player2Name = currentPlayerId === 'player2' ? currentPlayerName : otherPlayerName || '';

  // Deck selection phase
  if (phase === 'deck-selection' && !currentPlayerReady) {
    return (
      <div>
        <LobbyHeader gameCode={gameCode} onBack={onBack} />
        
        <PlayersBanner
          player1Name={player1Name}
          player2Name={player2Name}
          currentPlayerId={currentPlayerId}
        />

        {error && (
          <div className="bg-red-900/30 border-2 border-red-500 rounded p-4 max-w-2xl mx-auto mt-4">
            <div className="text-red-200">{error}</div>
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
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Back Button */}
        <button
          onClick={onBack}
          className="mb-8 text-xl text-gray-400 hover:text-game-highlight transition-colors flex items-center gap-2 font-semibold"
        >
          <span className="text-2xl">←</span> Leave Lobby
        </button>

        {/* Game Code Display */}
        <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600 mb-6">
          <GameCodeDisplay 
            code={gameCode} 
            size="large" 
            label="Share this code with your friend:" 
          />
        </div>

        {/* Players Status */}
        <div className="mb-6">
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
        <WaitingStatus phase={phase} currentPlayerId={currentPlayerId} />
      </div>
    </div>
  );
}

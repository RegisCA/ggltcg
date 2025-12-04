/**
 * Lobby Join Component
 * Join an existing game lobby using a game code
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';
import { joinLobby } from '../api/gameService';

interface LobbyJoinProps {
  onLobbyJoined: (gameId: string, gameCode: string, player1Name: string, player1Id: string) => void;
  onBack: () => void;
}

export function LobbyJoin({ onLobbyJoined, onBack }: LobbyJoinProps) {
  const { user } = useAuth();
  const [gameCode, setGameCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playerName = user?.display_name || 'Player';
  const playerId = user?.google_id || '';

  const handleJoin = async () => {
    if (!playerId) {
      setError('You must be logged in to join a game');
      return;
    }

    if (!gameCode.trim()) {
      setError('Please enter a game code');
      return;
    }

    // Validate game code format (6 alphanumeric characters)
    const cleanCode = gameCode.trim().toUpperCase();
    if (!/^[A-Z0-9]{6}$/.test(cleanCode)) {
      setError('Game code must be 6 characters (letters and numbers only)');
      return;
    }

    setIsJoining(true);
    setError(null);

    try {
      const response = await joinLobby(cleanCode, { 
        player2_id: playerId,
        player2_name: playerName 
      });
      onLobbyJoined(response.game_id, response.game_code, response.player1_name, response.player1_id);
    } catch (err: unknown) {
      console.error('Failed to join lobby:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const errorMsg = (err as any).response?.data?.detail || 'Failed to join lobby. Please check the game code and try again.';
      setError(errorMsg);
    } finally {
      setIsJoining(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && gameCode.trim() && !isJoining) {
      handleJoin();
    }
  };

  const handleGameCodeChange = (value: string) => {
    // Only allow alphanumeric characters, max 6
    const cleaned = value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
    setGameCode(cleaned);
  };

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="max-w-md w-full">
        {/* Back Button */}
        <div style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <Button variant="ghost" size="md" onClick={onBack}>
            ← Back to Main Menu
          </Button>
        </div>

        {/* Title */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1 className="text-5xl font-bold text-game-highlight" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Join Game</h1>
          <p className="text-xl text-gray-200 font-semibold">Enter a game code to join as <span className="text-game-highlight">{playerName}</span></p>
        </div>

        {/* Form */}
        <div className="modal-padding bg-gray-800 rounded-lg border-2 border-gray-600">
          <div className="content-spacing">
            {/* Game Code Input */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-gray-300">
                Game Code
              </label>
              <input
                type="text"
                value={gameCode}
                onChange={(e) => handleGameCodeChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="6-character code"
                maxLength={6}
                disabled={isJoining}
                autoFocus
                className={`
                  w-full px-4 py-3 rounded bg-gray-700 border-2 text-2xl font-mono text-center tracking-widest
                  focus:outline-none focus:border-game-highlight transition-colors uppercase
                  ${isJoining ? 'opacity-50 cursor-not-allowed' : 'border-gray-600'}
                `}
              />
              <p className="text-xs text-gray-400 mt-1 text-center">
                Example: 9P47XA
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900/30 border-2 border-red-500 rounded p-3 text-red-200 text-sm">
                {error}
              </div>
            )}

            {/* Join Button */}
            <button
              onClick={handleJoin}
              disabled={!gameCode.trim() || isJoining}
              className={`
                w-full py-4 rounded-lg font-bold text-xl transition-all
                ${!gameCode.trim() || isJoining
                  ? 'bg-gray-600 cursor-not-allowed opacity-50'
                  : 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                }
              `}
            >
              {isJoining ? 'Joining Game...' : 'Join Game 🔗'}
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 bg-purple-900/20 border-2 border-purple-500/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="text-2xl">💡</div>
            <div className="text-sm text-gray-300">
              <p className="font-semibold mb-1">Need a game code?</p>
              <p className="text-gray-400">
                Ask your friend to create a game and share the 6-character code with you.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Lobby Create Component
 * Create a new game lobby and display game code for sharing
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';
import { createLobby } from '../api/gameService';

interface LobbyCreateProps {
  onLobbyCreated: (gameId: string, gameCode: string) => void;
  onBack: () => void;
}

export function LobbyCreate({ onLobbyCreated, onBack }: LobbyCreateProps) {
  const { user } = useAuth();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playerName = user?.display_name || 'Player';
  const playerId = user?.google_id || '';

  const handleCreate = async () => {
    if (!playerId) {
      setError('You must be logged in to create a game');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const response = await createLobby({ 
        player1_id: playerId,
        player1_name: playerName 
      });
      onLobbyCreated(response.game_id, response.game_code);
    } catch (err: unknown) {
      console.error('Failed to create lobby:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any).response?.data?.detail || 'Failed to create lobby. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Back Button */}
        <div className="mb-8">
          <Button variant="ghost" size="md" onClick={onBack}>
            ← Back to Main Menu
          </Button>
        </div>

        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold mb-3 text-game-highlight">Create Game</h1>
          <p className="text-xl text-gray-200 font-semibold">Start a new game as <span className="text-game-highlight">{playerName}</span></p>
        </div>

        {/* Form */}
        <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600">
          <div className="space-y-6">
            {/* Error Message */}
            {error && (
              <div className="bg-red-900/30 border-2 border-red-500 rounded p-3 text-red-200">
                {error}
              </div>
            )}

            {/* Create Button */}
            <button
              onClick={handleCreate}
              disabled={isCreating}
              className={`
                w-full py-4 rounded-lg font-bold text-xl transition-all
                ${isCreating
                  ? 'bg-gray-600 cursor-not-allowed opacity-50'
                  : 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                }
              `}
            >
              {isCreating ? 'Creating Lobby...' : 'Create Lobby 🎮'}
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 bg-purple-900/20 border-2 border-purple-500/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="text-2xl">ℹ️</div>
            <div className="text-sm text-gray-300">
              <p className="font-semibold mb-1">What happens next?</p>
              <ul className="space-y-1 text-gray-400">
                <li>• You'll receive a 6-character game code</li>
                <li>• Share the code with your friend</li>
                <li>• Both players select decks</li>
                <li>• Game starts automatically!</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

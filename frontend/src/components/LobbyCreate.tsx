/**
 * Lobby Create Component
 * Create a new game lobby and display game code for sharing
 */

import { useState } from 'react';
import { createLobby } from '../api/gameService';

interface LobbyCreateProps {
  onLobbyCreated: (gameId: string, gameCode: string, playerName: string) => void;
  onBack: () => void;
}

export function LobbyCreate({ onLobbyCreated, onBack }: LobbyCreateProps) {
  const [playerName, setPlayerName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!playerName.trim()) {
      setError('Please enter your name');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const response = await createLobby({ player1_name: playerName.trim() });
      onLobbyCreated(response.game_id, response.game_code, playerName.trim());
    } catch (err: any) {
      console.error('Failed to create lobby:', err);
      setError(err.response?.data?.detail || 'Failed to create lobby. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && playerName.trim() && !isCreating) {
      handleCreate();
    }
  };

  return (
    <div className="min-h-screen bg-game-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Back Button */}
        <button
          onClick={onBack}
          className="mb-8 text-xl text-gray-400 hover:text-game-highlight transition-colors flex items-center gap-2 font-semibold"
        >
          <span className="text-2xl">←</span> Back to Menu
        </button>

        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold mb-3 text-game-highlight">Create Game</h1>
          <p className="text-xl text-gray-200 font-semibold">Enter your name to start a new game</p>
        </div>

        {/* Form */}
        <div className="bg-gray-800 rounded-lg p-8 border-2 border-gray-600">
          <div className="space-y-6">
            {/* Player Name Input */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-gray-300">
                Your Name
              </label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Enter your name..."
                maxLength={50}
                disabled={isCreating}
                autoFocus
                className={`
                  w-full px-4 py-3 rounded bg-gray-700 border-2 text-lg
                  focus:outline-none focus:border-game-highlight transition-colors
                  ${isCreating ? 'opacity-50 cursor-not-allowed' : 'border-gray-600'}
                `}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900/30 border-2 border-red-500 rounded p-3 text-red-200">
                {error}
              </div>
            )}

            {/* Create Button */}
            <button
              onClick={handleCreate}
              disabled={!playerName.trim() || isCreating}
              className={`
                w-full py-4 rounded-lg font-bold text-xl transition-all
                ${!playerName.trim() || isCreating
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

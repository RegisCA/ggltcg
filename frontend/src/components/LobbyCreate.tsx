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
          <h1 className="text-5xl font-bold text-game-highlight" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Create Game</h1>
          <p className="text-xl text-gray-200 font-semibold">Start a new game as <span className="text-game-highlight">{playerName}</span></p>
        </div>

        {/* Form */}
        <div className="modal-padding bg-gray-800 rounded-lg border-2 border-gray-600">
          <div className="content-spacing">
            {/* Error Message */}
            {error && (
              <div 
                className="bg-red-900/30 border-2 border-red-500 rounded text-red-200"
                style={{ padding: 'var(--spacing-component-sm)' }}
              >
                {error}
              </div>
            )}

            {/* Create Button */}
            <button
              onClick={handleCreate}
              disabled={isCreating}
              className={`w-full rounded-lg font-bold text-xl transition-all ${
                isCreating
                  ? 'bg-gray-600 cursor-not-allowed opacity-50'
                  : 'bg-game-highlight hover:bg-red-600 cursor-pointer'
              }`}
              style={{ padding: 'var(--spacing-component-md) 0' }}
            >
              {isCreating ? 'Creating Lobby...' : 'Create Lobby 🎮'}
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div 
          className="bg-purple-900/20 border-2 border-purple-500/50 rounded-lg"
          style={{ marginTop: 'var(--spacing-component-lg)', padding: 'var(--spacing-component-md)' }}
        >
          <div className="flex items-start" style={{ gap: 'var(--spacing-component-sm)' }}>
            <div className="text-2xl">ℹ️</div>
            <div className="text-sm text-gray-300">
              <p className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>What happens next?</p>
              <ul className="content-spacing text-gray-400">
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

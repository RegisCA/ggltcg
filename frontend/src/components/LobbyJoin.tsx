/**
 * Lobby Join Component
 * Join an existing game lobby using a game code
 */

import { useState } from 'react';
import { joinLobby } from '../api/gameService';

interface LobbyJoinProps {
  onLobbyJoined: (gameId: string, gameCode: string, player1Name: string, player2Name: string) => void;
  onBack: () => void;
}

export function LobbyJoin({ onLobbyJoined, onBack }: LobbyJoinProps) {
  const [playerName, setPlayerName] = useState('');
  const [gameCode, setGameCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleJoin = async () => {
    if (!playerName.trim()) {
      setError('Please enter your name');
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
      const response = await joinLobby(cleanCode, { player2_name: playerName.trim() });
      onLobbyJoined(response.game_id, response.game_code, response.player1_name, playerName.trim());
    } catch (err: any) {
      console.error('Failed to join lobby:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to join lobby. Please check the game code and try again.';
      setError(errorMsg);
    } finally {
      setIsJoining(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && playerName.trim() && gameCode.trim() && !isJoining) {
      handleJoin();
    }
  };

  const handleGameCodeChange = (value: string) => {
    // Only allow alphanumeric characters, max 6
    const cleaned = value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
    setGameCode(cleaned);
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
          <h1 className="text-5xl font-bold mb-3 text-game-highlight">Join Game</h1>
          <p className="text-xl text-gray-200 font-semibold">Enter the game code from your friend</p>
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
                disabled={isJoining}
                autoFocus
                className={`
                  w-full px-4 py-3 rounded bg-gray-700 border-2 text-lg
                  focus:outline-none focus:border-game-highlight transition-colors
                  ${isJoining ? 'opacity-50 cursor-not-allowed' : 'border-gray-600'}
                `}
              />
            </div>

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
              disabled={!playerName.trim() || !gameCode.trim() || isJoining}
              className={`
                w-full py-4 rounded-lg font-bold text-xl transition-all
                ${!playerName.trim() || !gameCode.trim() || isJoining
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

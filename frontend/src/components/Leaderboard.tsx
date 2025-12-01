/**
 * Leaderboard Component
 * Displays top players ranked by win rate
 */

import { useState, useEffect } from 'react';
import { getLeaderboard } from '../api/statsService';
import type { LeaderboardResponse, LeaderboardEntry } from '../types/api';

interface LeaderboardProps {
  onClose: () => void;
  onViewPlayer?: (playerId: string) => void;
}

export function Leaderboard({ onClose, onViewPlayer }: LeaderboardProps) {
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLeaderboard() {
      try {
        setLoading(true);
        setError(null);
        const data = await getLeaderboard(10, 1); // Top 10, min 1 game for now
        setLeaderboard(data);
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
        setError('Failed to load leaderboard');
      } finally {
        setLoading(false);
      }
    }

    fetchLeaderboard();
  }, []);

  const getRankEmoji = (rank: number): string => {
    switch (rank) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return `#${rank}`;
    }
  };

  const getRankColor = (rank: number): string => {
    switch (rank) {
      case 1: return 'text-yellow-400';
      case 2: return 'text-gray-300';
      case 3: return 'text-amber-600';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border-4 border-game-highlight max-w-xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold text-game-highlight">🏆 Leaderboard</h2>
            <p className="text-gray-400 mt-1">
              Top players by win rate
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl font-bold p-2"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading && (
            <div className="text-center py-8">
              <div className="text-4xl mb-4 animate-bounce">🎲</div>
              <p className="text-gray-400">Loading leaderboard...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <div className="text-4xl mb-4">😢</div>
              <p className="text-red-400">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length === 0 && (
            <div className="text-center py-8">
              <div className="text-4xl mb-4">🎮</div>
              <p className="text-gray-400">No players on the leaderboard yet!</p>
              <p className="text-gray-500 text-sm mt-2">
                Play some games to be the first!
              </p>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length > 0 && (
            <div className="space-y-3">
              {leaderboard.entries.map((entry: LeaderboardEntry) => (
                <div
                  key={entry.player_id}
                  onClick={() => onViewPlayer?.(entry.player_id)}
                  className={`
                    flex items-center gap-4 p-4 rounded-lg bg-gray-700/50 
                    ${onViewPlayer ? 'cursor-pointer hover:bg-gray-700' : ''}
                    transition-colors
                  `}
                >
                  {/* Rank */}
                  <div className={`text-2xl font-bold w-12 text-center ${getRankColor(entry.rank)}`}>
                    {getRankEmoji(entry.rank)}
                  </div>

                  {/* Player Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-lg truncate">
                      {entry.display_name}
                    </div>
                    <div className="text-sm text-gray-400">
                      {entry.games_won}W / {entry.games_played - entry.games_won}L
                    </div>
                  </div>

                  {/* Win Rate */}
                  <div className="text-right">
                    <div className={`
                      text-xl font-bold
                      ${entry.win_rate >= 70 ? 'text-green-400' : ''}
                      ${entry.win_rate >= 50 && entry.win_rate < 70 ? 'text-yellow-400' : ''}
                      ${entry.win_rate < 50 ? 'text-red-400' : ''}
                    `}>
                      {entry.win_rate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">
                      {entry.games_played} games
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {!loading && !error && leaderboard && (
          <div className="p-4 border-t border-gray-700 text-center text-gray-500 text-sm">
            Minimum {leaderboard.min_games_required} game{leaderboard.min_games_required !== 1 ? 's' : ''} required to qualify
          </div>
        )}
      </div>
    </div>
  );
}

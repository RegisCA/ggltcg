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

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getLeaderboard(10, 3); // Top 10, min 3 games to match backend default
      setLeaderboard(data);
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
      setError('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

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
    <div 
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.80)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem'
      }}
    >
      <div 
        className="bg-gray-900/95 rounded-xl border-4 border-game-highlight shadow-2xl flex flex-col"
        style={{ 
          width: '600px',
          maxHeight: '80vh',
        }}
      >
        {/* Header */}
        <div className="border-b-4 border-game-accent bg-gray-800 flex-shrink-0" style={{ padding: 'var(--spacing-component-md)' }}>
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold text-game-highlight">🏆 Leaderboard</h2>
              <p className="text-gray-300" style={{ marginTop: '4px' }}>
                Top players by win rate
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-2xl font-bold" style={{ padding: '4px' }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          {loading && (
            <div className="text-center py-8">
              <div className="text-4xl animate-bounce" style={{ marginBottom: 'var(--spacing-component-md)' }}>🎲</div>
              <p className="text-gray-400">Loading leaderboard...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <div className="text-4xl" style={{ marginBottom: 'var(--spacing-component-md)' }}>😢</div>
              <p className="text-red-400">{error}</p>
              <button
                onClick={fetchLeaderboard}
                className="bg-gray-700 hover:bg-gray-600 rounded-lg" style={{ marginTop: 'var(--spacing-component-md)', padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length === 0 && (
            <div className="text-center py-8">
              <div className="text-4xl" style={{ marginBottom: 'var(--spacing-component-md)' }}>🎮</div>
              <p className="text-gray-400">No players on the leaderboard yet!</p>
              <p className="text-gray-500 text-sm" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                Play some games to be the first!
              </p>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length > 0 && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              {leaderboard.entries.map((entry: LeaderboardEntry) => (
                <div
                  key={entry.player_id}
                  onClick={() => onViewPlayer?.(entry.player_id)}
                  className={`
                    flex items-center rounded-lg bg-gray-700/50 
                    ${onViewPlayer ? 'cursor-pointer hover:bg-gray-700' : ''}
                    transition-colors
                  `}
                  style={{ gap: 'var(--spacing-component-md)', padding: 'var(--spacing-component-md)' }}
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
                  <div className="text-right" style={{ paddingRight: 'var(--spacing-component-sm)' }}>
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
          <div className="border-t border-gray-700 text-center text-gray-500 text-sm" style={{ padding: 'var(--spacing-component-md)' }}>
            Minimum {leaderboard.min_games_required} game{leaderboard.min_games_required !== 1 ? 's' : ''} required to qualify
          </div>
        )}
      </div>
    </div>
  );
}

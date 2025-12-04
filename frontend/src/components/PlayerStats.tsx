/**
 * PlayerStats Component
 * Displays detailed statistics for a single player
 */

import { useState, useEffect } from 'react';
import { getPlayerStats } from '../api/statsService';
import type { PlayerStats as PlayerStatsType, CardStats } from '../types/api';

interface PlayerStatsProps {
  playerId: string;
  onClose: () => void;
}

export function PlayerStats({ playerId, onClose }: PlayerStatsProps) {
  const [stats, setStats] = useState<PlayerStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        setLoading(true);
        setError(null);
        const data = await getPlayerStats(playerId);
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch player stats:', err);
        setError('Failed to load player stats');
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, [playerId]);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const getWinRateColor = (rate: number): string => {
    if (rate >= 70) return 'text-green-400';
    if (rate >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border-4 border-purple-500 max-w-xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-700 flex justify-between items-center" style={{ padding: 'var(--spacing-component-lg)' }}>
          <div>
            <h2 className="text-3xl font-bold text-purple-400">📊 Player Stats</h2>
            {stats && (
              <p className="text-xl text-gray-200 mt-1 font-semibold">
                {stats.display_name}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl font-bold p-2"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          {loading && (
            <div className="text-center py-8">
              <div className="text-4xl mb-4 animate-bounce">📈</div>
              <p className="text-gray-400">Loading stats...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <div className="text-4xl mb-4">😢</div>
              <p className="text-red-400">{error}</p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Close
              </button>
            </div>
          )}

          {!loading && !error && stats && (
            <div className="space-y-6">
              {/* Overall Stats */}
              <div className="grid grid-cols-2 gap-4">
                {/* Win Rate */}
                <div className="bg-gray-900/90 rounded-lg p-4 text-center">
                  <div className={`text-3xl font-bold ${getWinRateColor(stats.win_rate)}`}>
                    {stats.win_rate.toFixed(1)}%
                  </div>
                  <div className="text-gray-300 text-sm">Win Rate</div>
                </div>

                {/* Games */}
                <div className="bg-gray-900/90 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-400">
                    {stats.games_played}
                  </div>
                  <div className="text-gray-300 text-sm">Games Played</div>
                </div>

                {/* Wins */}
                <div className="bg-gray-900/90 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-400">
                    {stats.games_won}
                  </div>
                  <div className="text-gray-300 text-sm">Wins</div>
                </div>

                {/* Losses */}
                <div className="bg-gray-900/90 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-400">
                    {stats.games_played - stats.games_won}
                  </div>
                  <div className="text-gray-300 text-sm">Losses</div>
                </div>
              </div>

              {/* Tussle Stats */}
              {stats.total_tussles > 0 && (
                <div className="bg-gray-900/90 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-3 text-orange-400">⚔️ Tussle Stats</h3>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-white">{stats.total_tussles}</div>
                      <div className="text-gray-300 text-sm">Initiated</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-400">{stats.tussles_won}</div>
                      <div className="text-gray-300 text-sm">Won</div>
                    </div>
                    <div>
                      <div className={`text-2xl font-bold ${getWinRateColor(stats.tussle_win_rate)}`}>
                        {stats.tussle_win_rate.toFixed(1)}%
                      </div>
                      <div className="text-gray-300 text-sm">Win Rate</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Card Stats */}
              {stats.card_stats && stats.card_stats.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-cyan-400">🃏 Card Usage</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {stats.card_stats.map((card: CardStats) => (
                      <div
                        key={card.card_name}
                        className="flex items-center gap-3 p-3 bg-gray-900/90 rounded-lg"
                      >
                        <div className="flex-1 font-medium text-white">{card.card_name}</div>
                        <div className="text-sm text-gray-300">
                          {card.games_won}W / {card.games_played - card.games_won}L
                        </div>
                        <div className={`font-bold ${getWinRateColor(card.win_rate)}`} style={{ paddingRight: 'var(--spacing-component-sm)' }}>
                          {card.win_rate.toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

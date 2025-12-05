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
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="bg-gray-800 rounded-xl border-4 border-purple-500 max-w-xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-700 flex justify-between items-center" style={{ padding: 'var(--spacing-component-lg)' }}>
          <div>
            <h2 className="text-3xl font-bold text-purple-400">📊 Player Stats</h2>
            {stats && (
              <p className="text-xl text-gray-200 font-semibold" style={{ marginTop: '4px' }}>
                {stats.display_name}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl font-bold" style={{ padding: 'var(--spacing-component-xs)' }}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          {loading && (
            <div className="text-center py-8">
              <div className="text-4xl animate-bounce" style={{ marginBottom: 'var(--spacing-component-md)' }}>📈</div>
              <p className="text-gray-400">Loading stats...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <div className="text-4xl" style={{ marginBottom: 'var(--spacing-component-md)' }}>😢</div>
              <p className="text-red-400">{error}</p>
              <button
                onClick={onClose}
                className="bg-gray-700 hover:bg-gray-600 rounded-lg" style={{ marginTop: 'var(--spacing-component-md)', padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
              >
                Close
              </button>
            </div>
          )}

          {!loading && !error && stats && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-lg)' }}>
              {/* Overall Stats */}
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-md)' }}>
                {/* Win Rate */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-md)' }}>
                  <div className={`text-3xl font-bold ${getWinRateColor(stats.win_rate)}`}>
                    {stats.win_rate.toFixed(1)}%
                  </div>
                  <div className="text-gray-300 text-sm">Win Rate</div>
                </div>

                {/* Games */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-md)' }}>
                  <div className="text-3xl font-bold text-blue-400">
                    {stats.games_played}
                  </div>
                  <div className="text-gray-300 text-sm">Games Played</div>
                </div>

                {/* Wins */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-md)' }}>
                  <div className="text-3xl font-bold text-green-400">
                    {stats.games_won}
                  </div>
                  <div className="text-gray-300 text-sm">Wins</div>
                </div>

                {/* Losses */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-md)' }}>
                  <div className="text-3xl font-bold text-red-400">
                    {stats.games_played - stats.games_won}
                  </div>
                  <div className="text-gray-300 text-sm">Losses</div>
                </div>
              </div>

              {/* Tussle Stats */}
              {stats.total_tussles > 0 && (
                <div className="bg-gray-900/90 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
                  <h3 className="text-lg font-semibold text-orange-400" style={{ marginBottom: 'var(--spacing-component-sm)' }}>⚔️ Tussle Stats</h3>
                  <div className="grid grid-cols-3 text-center" style={{ gap: 'var(--spacing-component-md)' }}>
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
                  <h3 className="text-lg font-semibold text-cyan-400" style={{ marginBottom: 'var(--spacing-component-sm)' }}>🃏 Card Usage</h3>
                  <div className="flex flex-col max-h-48 overflow-y-auto" style={{ gap: 'var(--spacing-component-xs)' }}>
                    {stats.card_stats.map((card: CardStats) => (
                      <div
                        key={card.card_name}
                        className="flex items-center bg-gray-900/90 rounded-lg"
                        style={{ gap: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-sm)' }}
                      >
                        <div className="flex-1 font-medium text-white" style={{ paddingLeft: 'var(--spacing-component-sm)' }}>{card.card_name}</div>
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
        <div className="border-t border-gray-700" style={{ padding: 'var(--spacing-component-md)' }}>
          <button
            onClick={onClose}
            className="w-full bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition-colors"
            style={{ padding: 'var(--spacing-component-sm)' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

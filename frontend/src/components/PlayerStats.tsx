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

type SortField = 'card_name' | 'games_won' | 'games_lost' | 'win_rate';
type SortDirection = 'asc' | 'desc';

export function PlayerStats({ playerId, onClose }: PlayerStatsProps) {
  const [stats, setStats] = useState<PlayerStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('win_rate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

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

  const getHeatmapColor = (rate: number): string => {
    // Background colors for heatmap (more subtle than text colors)
    if (rate >= 80) return 'bg-green-900/60';
    if (rate >= 70) return 'bg-green-900/40';
    if (rate >= 60) return 'bg-yellow-900/40';
    if (rate >= 50) return 'bg-yellow-900/30';
    if (rate >= 40) return 'bg-orange-900/30';
    if (rate >= 30) return 'bg-red-900/30';
    return 'bg-red-900/50';
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if clicking same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Default to desc for numeric fields, asc for name
      setSortField(field);
      setSortDirection(field === 'card_name' ? 'asc' : 'desc');
    }
  };

  const getSortedCardStats = (cardStats: CardStats[]): CardStats[] => {
    return [...cardStats].sort((a, b) => {
      let comparison = 0;
      
      switch (sortField) {
        case 'card_name':
          comparison = a.card_name.localeCompare(b.card_name);
          break;
        case 'games_won':
          comparison = a.games_won - b.games_won;
          break;
        case 'games_lost':
          comparison = (a.games_played - a.games_won) - (b.games_played - b.games_won);
          break;
        case 'win_rate':
          comparison = a.win_rate - b.win_rate;
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  };

  const getSortIcon = (field: SortField): string => {
    if (sortField !== field) return '↕️';
    return sortDirection === 'asc' ? '↑' : '↓';
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
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0' }}>
              <div className="text-4xl animate-bounce" style={{ marginBottom: 'var(--spacing-component-md)' }}>📈</div>
              <p className="text-gray-400">Loading stats...</p>
            </div>
          )}

          {error && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0' }}>
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
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
              {/* Overall Stats - top row: 3 columns */}
              <div className="grid grid-cols-3" style={{ gap: 'var(--spacing-component-sm)' }}>
                {/* Win Rate */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-sm)' }}>
                  <div className={`text-2xl font-bold ${getWinRateColor(stats.win_rate)}`}>
                    {stats.win_rate.toFixed(1)}%
                  </div>
                  <div className="text-gray-300 text-xs">Win Rate</div>
                </div>

                {/* Games */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-sm)' }}>
                  <div className="text-2xl font-bold text-blue-400">
                    {stats.games_played}
                  </div>
                  <div className="text-gray-300 text-xs">Games</div>
                </div>

                {/* Record */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-sm)' }}>
                  <div className="text-2xl font-bold text-green-400">
                    {stats.games_won}W / {stats.games_played - stats.games_won}L
                  </div>
                  <div className="text-gray-300 text-xs">Record</div>
                </div>
              </div>

              {/* Second row: 2 columns for avg stats */}
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                {/* Avg Turns */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-sm)' }}>
                  <div className="text-2xl font-bold text-orange-400">
                    {stats.avg_turns.toFixed(1)}
                  </div>
                  <div className="text-gray-300 text-xs">Avg Turns</div>
                </div>

                {/* Avg Duration */}
                <div className="bg-gray-900/90 rounded-lg text-center" style={{ padding: 'var(--spacing-component-sm)' }}>
                  <div className="text-2xl font-bold text-cyan-400">
                    {stats.avg_game_duration_seconds < 60 
                      ? `${Math.round(stats.avg_game_duration_seconds)}s`
                      : `${Math.floor(stats.avg_game_duration_seconds / 60)}m ${Math.round(stats.avg_game_duration_seconds % 60)}s`
                    }
                  </div>
                  <div className="text-gray-300 text-xs">Avg Game</div>
                </div>
              </div>

              {/* Card Stats */}
              {stats.card_stats && stats.card_stats.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-cyan-400" style={{ marginBottom: 'var(--spacing-component-sm)' }}>🃏 Card Usage</h3>
                  
                  {/* Column Headers */}
                  <div className="flex items-center bg-gray-950/80 rounded-t-lg font-semibold text-xs text-gray-400 uppercase" style={{ gap: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-xs) var(--spacing-component-sm)' }}>
                    <button
                      onClick={() => handleSort('card_name')}
                      className="flex-1 text-left hover:text-cyan-400 transition-colors"
                    >
                      Card {getSortIcon('card_name')}
                    </button>
                    <button
                      onClick={() => handleSort('games_won')}
                      className="w-16 text-center hover:text-cyan-400 transition-colors"
                    >
                      Wins {getSortIcon('games_won')}
                    </button>
                    <button
                      onClick={() => handleSort('games_lost')}
                      className="w-16 text-center hover:text-cyan-400 transition-colors"
                    >
                      Loss {getSortIcon('games_lost')}
                    </button>
                    <button
                      onClick={() => handleSort('win_rate')}
                      className="w-16 text-center hover:text-cyan-400 transition-colors"
                    >
                      Rate {getSortIcon('win_rate')}
                    </button>
                  </div>

                  <div className="flex flex-col max-h-48 overflow-y-auto">
                    {getSortedCardStats(stats.card_stats).map((card: CardStats) => {
                      const gamesLost = card.games_played - card.games_won;
                      return (
                        <div
                          key={card.card_name}
                          className={`flex items-center ${getHeatmapColor(card.win_rate)} hover:brightness-125 transition-all`}
                          style={{ gap: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-xs) var(--spacing-component-sm)' }}
                        >
                          <div className="flex-1 font-medium text-white">{card.card_name}</div>
                          <div className="w-16 text-center text-sm text-green-300">
                            {card.games_won}
                          </div>
                          <div className="w-16 text-center text-sm text-red-300">
                            {gamesLost}
                          </div>
                          <div className={`w-16 text-center font-bold ${getWinRateColor(card.win_rate)}`}>
                            {card.win_rate.toFixed(0)}%
                          </div>
                        </div>
                      );
                    })}
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

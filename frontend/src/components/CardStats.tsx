/**
 * CardStats Component
 * Displays per-card statistics aggregated across all players
 */

import { useState, useEffect } from 'react';
import { getCardStats } from '../api/statsService';
import type { CardAggregateEntry } from '../types/api';

interface CardStatsProps {
  onClose: () => void;
}

type SortField =
  | 'card_name'
  | 'games_played'
  | 'games_won'
  | 'games_lost'
  | 'win_rate'
  | 'pick_rate'
  | 'player_count';
type SortDirection = 'asc' | 'desc';

export function CardStats({ onClose }: CardStatsProps) {
  const [cards, setCards] = useState<CardAggregateEntry[] | null>(null);
  const [totalGames, setTotalGames] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('win_rate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    async function fetchCardStats() {
      try {
        setLoading(true);
        setError(null);
        const data = await getCardStats(200, 1);
        setCards(data.entries);
        setTotalGames(data.total_games);
      } catch (err) {
        console.error('Failed to fetch card stats:', err);
        setError('Failed to load card stats');
      } finally {
        setLoading(false);
      }
    }

    fetchCardStats();
  }, []);

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
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'card_name' ? 'asc' : 'desc');
    }
  };

  const getSortedCards = (cardStats: CardAggregateEntry[]): CardAggregateEntry[] => {
    return [...cardStats].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'card_name':
          comparison = a.card_name.localeCompare(b.card_name);
          break;
        case 'games_played':
          comparison = a.games_played - b.games_played;
          break;
        case 'games_won':
          comparison = a.games_won - b.games_won;
          break;
        case 'games_lost':
          comparison = a.games_lost - b.games_lost;
          break;
        case 'win_rate':
          comparison = a.win_rate - b.win_rate;
          break;
        case 'pick_rate':
          comparison = a.pick_rate - b.pick_rate;
          break;
        case 'player_count':
          comparison = a.player_count - b.player_count;
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
      <div className="bg-gray-800 rounded-xl border-4 border-purple-500 max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-700 flex justify-between items-center" style={{ padding: 'var(--spacing-component-lg)' }}>
          <div>
            <h2 className="text-3xl font-bold text-purple-400">🃏 Card Stats</h2>
            <p className="text-sm text-gray-400" style={{ marginTop: '4px' }}>
              Aggregated across all players · usage = deck inclusion
            </p>
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
              <div className="text-4xl animate-bounce" style={{ marginBottom: 'var(--spacing-component-md)' }}>📊</div>
              <p className="text-gray-400">Loading card stats...</p>
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

          {!loading && !error && cards && cards.length === 0 && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0' }}>
              <div className="text-4xl" style={{ marginBottom: 'var(--spacing-component-md)' }}>🤷</div>
              <p className="text-gray-400">No card data yet — play some games!</p>
            </div>
          )}

          {!loading && !error && cards && cards.length > 0 && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              <p className="text-xs text-gray-400">
                {cards.length} cards · {totalGames} total deck slots played
              </p>

              {/* Column Headers */}
              <div className="flex items-center bg-gray-950/80 rounded-t-lg font-semibold text-xs text-gray-400 uppercase" style={{ gap: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-xs) var(--spacing-component-sm)' }}>
                <button
                  onClick={() => handleSort('card_name')}
                  className="flex-1 text-left hover:text-cyan-400 transition-colors"
                >
                  Card {getSortIcon('card_name')}
                </button>
                <button
                  onClick={() => handleSort('games_played')}
                  className="w-14 text-center hover:text-cyan-400 transition-colors"
                >
                  Picked {getSortIcon('games_played')}
                </button>
                <button
                  onClick={() => handleSort('pick_rate')}
                  className="w-14 text-center hover:text-cyan-400 transition-colors"
                >
                  Pick% {getSortIcon('pick_rate')}
                </button>
                <button
                  onClick={() => handleSort('player_count')}
                  className="w-14 text-center hover:text-cyan-400 transition-colors"
                >
                  Plyrs {getSortIcon('player_count')}
                </button>
                <button
                  onClick={() => handleSort('games_won')}
                  className="w-12 text-center hover:text-cyan-400 transition-colors"
                >
                  W {getSortIcon('games_won')}
                </button>
                <button
                  onClick={() => handleSort('games_lost')}
                  className="w-12 text-center hover:text-cyan-400 transition-colors"
                >
                  L {getSortIcon('games_lost')}
                </button>
                <button
                  onClick={() => handleSort('win_rate')}
                  className="w-14 text-center hover:text-cyan-400 transition-colors"
                >
                  Rate {getSortIcon('win_rate')}
                </button>
              </div>

              <div className="flex flex-col" style={{ marginTop: 'calc(-1 * var(--spacing-component-sm))' }}>
                {getSortedCards(cards).map((card) => (
                  <div
                    key={card.card_name}
                    className={`flex items-center ${getHeatmapColor(card.win_rate)} hover:brightness-125 transition-all`}
                    style={{ gap: 'var(--spacing-component-sm)', padding: 'var(--spacing-component-xs) var(--spacing-component-sm)' }}
                  >
                    <div className="flex-1 font-medium text-white">{card.card_name}</div>
                    <div className="w-14 text-center text-sm text-gray-200">{card.games_played}</div>
                    <div className="w-14 text-center text-sm text-gray-300">{card.pick_rate.toFixed(1)}%</div>
                    <div className="w-14 text-center text-sm text-gray-300">{card.player_count}</div>
                    <div className="w-12 text-center text-sm text-green-300">{card.games_won}</div>
                    <div className="w-12 text-center text-sm text-red-300">{card.games_lost}</div>
                    <div className={`w-14 text-center font-bold ${getWinRateColor(card.win_rate)}`}>
                      {card.win_rate.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
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

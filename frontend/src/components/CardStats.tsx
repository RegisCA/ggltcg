/**
 * CardStats Component
 * Displays per-card statistics aggregated across all players.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — same
 * dark-panel + gold-hairline idiom as Leaderboard.tsx / PlayerStats.tsx.
 *
 * Decorative emoji removed per §8 (🃏😢🤷); none of these are content-bearing
 * state badges.
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

  const winRateColor = (rate: number): string => {
    if (rate >= 70) return 'var(--gold)';
    if (rate >= 50) return 'var(--ink-text)';
    return 'var(--danger)';
  };

  const heatmapBg = (rate: number): string => {
    if (rate >= 80) return 'rgba(90,168,90,.22)';
    if (rate >= 70) return 'rgba(90,168,90,.14)';
    if (rate >= 60) return 'rgba(242,193,78,.14)';
    if (rate >= 50) return 'rgba(242,193,78,.09)';
    if (rate >= 40) return 'rgba(224,142,74,.10)';
    if (rate >= 30) return 'rgba(200,80,80,.10)';
    return 'rgba(200,80,80,.18)';
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

  const getSortIndicator = (field: SortField): string => {
    if (sortField !== field) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
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
        padding: 'var(--spacing-component-md)',
      }}
    >
      <div
        className="flex flex-col"
        style={{
          width: '720px',
          maxWidth: '100%',
          maxHeight: '85vh',
          background: '#241E17',
          borderRadius: '8px',
          border: '1px solid var(--gold)',
          boxShadow: '0 8px 24px rgba(0,0,0,.4)',
        }}
      >
        {/* Header */}
        <div
          className="flex-shrink-0 flex justify-between items-start"
          style={{
            padding: 'var(--spacing-component-md)',
            borderBottom: '1px solid rgba(242,193,78,.25)',
          }}
        >
          <div>
            <h2 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', color: 'var(--ink-text)' }}>
              Card Stats
            </h2>
            <p style={{ marginTop: '4px', fontSize: '13px', color: 'var(--ink-faint)' }}>
              Aggregated across all players — usage = deck inclusion
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close card stats"
            style={{
              fontSize: '22px',
              fontWeight: 900,
              color: 'var(--ink-faint)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto overflow-x-hidden flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          {loading && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0', color: 'var(--ink-muted)' }}>
              <p>Loading card stats...</p>
            </div>
          )}

          {error && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0' }}>
              <p style={{ color: 'var(--danger)' }}>{error}</p>
              <button
                onClick={onClose}
                style={{
                  marginTop: 'var(--spacing-component-md)',
                  padding: 'var(--spacing-component-xs) var(--spacing-component-md)',
                  borderRadius: '6px',
                  border: 'none',
                  background: 'rgba(237,232,222,.1)',
                  color: 'var(--ink-text)',
                  cursor: 'pointer',
                }}
              >
                Close
              </button>
            </div>
          )}

          {!loading && !error && cards && cards.length === 0 && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0', color: 'var(--ink-muted)' }}>
              <p>No card data yet — play some games!</p>
            </div>
          )}

          {!loading && !error && cards && cards.length > 0 && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              <p style={{ fontSize: '12px', color: 'var(--ink-faint)' }}>
                {cards.length} cards · {totalGames} total deck slots played
              </p>

              {/* Column Headers */}
              <div
                className="flex items-center overflow-x-auto"
                style={{
                  gap: 'var(--spacing-component-sm)',
                  padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                  background: 'rgba(0,0,0,.25)',
                  borderRadius: '6px 6px 0 0',
                  fontSize: '11px',
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  color: 'var(--ink-faint)',
                }}
              >
                <button
                  onClick={() => handleSort('card_name')}
                  className="flex-1 text-left"
                  style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', minWidth: '96px' }}
                >
                  Card{getSortIndicator('card_name')}
                </button>
                <button
                  onClick={() => handleSort('games_played')}
                  style={{ width: '52px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  Picked{getSortIndicator('games_played')}
                </button>
                <button
                  onClick={() => handleSort('pick_rate')}
                  style={{ width: '52px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  Pick%{getSortIndicator('pick_rate')}
                </button>
                <button
                  onClick={() => handleSort('player_count')}
                  style={{ width: '48px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  Plyrs{getSortIndicator('player_count')}
                </button>
                <button
                  onClick={() => handleSort('games_won')}
                  style={{ width: '40px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  W{getSortIndicator('games_won')}
                </button>
                <button
                  onClick={() => handleSort('games_lost')}
                  style={{ width: '40px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  L{getSortIndicator('games_lost')}
                </button>
                <button
                  onClick={() => handleSort('win_rate')}
                  style={{ width: '52px', flexShrink: 0, textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  Rate{getSortIndicator('win_rate')}
                </button>
              </div>

              <div className="flex flex-col overflow-x-auto">
                {getSortedCards(cards).map((card) => (
                  <div
                    key={card.card_name}
                    className="flex items-center"
                    style={{
                      gap: 'var(--spacing-component-sm)',
                      padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                      background: heatmapBg(card.win_rate),
                    }}
                  >
                    <div className="flex-1" style={{ minWidth: '96px', fontWeight: 700, color: 'var(--ink-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {card.card_name}
                    </div>
                    <div style={{ width: '52px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)' }}>{card.games_played}</div>
                    <div style={{ width: '52px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)' }}>{card.pick_rate.toFixed(1)}%</div>
                    <div style={{ width: '48px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)' }}>{card.player_count}</div>
                    <div style={{ width: '40px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)' }}>{card.games_won}</div>
                    <div style={{ width: '40px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-faint)' }}>{card.games_lost}</div>
                    <div style={{ width: '52px', flexShrink: 0, textAlign: 'center', fontWeight: 900, color: winRateColor(card.win_rate) }}>
                      {card.win_rate.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0" style={{ padding: 'var(--spacing-component-md)', borderTop: '1px solid rgba(237,232,222,.12)' }}>
          <button
            onClick={onClose}
            style={{
              width: '100%',
              padding: 'var(--spacing-component-sm)',
              borderRadius: '6px',
              border: 'none',
              fontWeight: 900,
              background: 'var(--gold)',
              color: 'var(--desk-bottom)',
              boxShadow: '0 3px 0 rgba(0,0,0,.5)',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

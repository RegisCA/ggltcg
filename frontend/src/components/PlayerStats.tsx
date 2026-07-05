/**
 * PlayerStats Component
 * Displays detailed statistics for a single player.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — no
 * mockup exists for this screen, so this applies the established
 * dark-panel + gold-hairline idiom from Leaderboard.tsx / VictoryScreen.tsx:
 * Gochi Hand header, gold accents, viewer-relative --you highlighting where
 * identity appears (this player's own row, if they're the viewer).
 *
 * Decorative emoji removed per §8 (📊🃏😢); none of these are content-bearing
 * state badges.
 */

import { useState, useEffect } from 'react';
import { getPlayerStats } from '../api/statsService';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { useAuth } from '../contexts/AuthContext';
import type { PlayerStats as PlayerStatsType, CardStats } from '../types/api';

interface PlayerStatsProps {
  playerId: string;
  onClose: () => void;
  /** Test/preview seam: when provided, skips the getPlayerStats() fetch and
   *  renders this canned payload instead. Production callers never pass
   *  this — used by the /design.html#player-stats fixture and component
   *  tests, mirroring Leaderboard's entriesOverride seam. */
  statsOverride?: PlayerStatsType;
}

type SortField = 'card_name' | 'games_won' | 'games_lost' | 'win_rate';
type SortDirection = 'asc' | 'desc';

export function PlayerStats({ playerId, onClose, statsOverride }: PlayerStatsProps) {
  const localPlayerId = useLocalPlayerId();
  const { user } = useAuth();
  const [stats, setStats] = useState<PlayerStatsType | null>(statsOverride ?? null);
  const [loading, setLoading] = useState(!statsOverride);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('win_rate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    if (statsOverride) return; // preview/test harness supplies stats directly

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
  }, [playerId, statsOverride]);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const viewerId = user?.google_id ?? localPlayerId;
  const isViewer = !!viewerId && viewerId === playerId;

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
          width: '600px',
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
              Player Stats
            </h2>
            {stats && (
              <p
                style={{
                  marginTop: '4px',
                  fontSize: '15px',
                  fontWeight: 700,
                  color: isViewer ? 'var(--you)' : 'var(--ink-muted)',
                }}
              >
                {stats.display_name}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close player stats"
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
              <p>Loading stats...</p>
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

          {!loading && !error && stats && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
              {/* Overall Stats - top row: 3 columns */}
              <div className="grid grid-cols-3" style={{ gap: 'var(--spacing-component-sm)' }}>
                <StatTile
                  value={`${stats.win_rate.toFixed(1)}%`}
                  label="Win Rate"
                  color={winRateColor(stats.win_rate)}
                />
                <StatTile
                  value={String(stats.games_played)}
                  label="Games"
                  color="var(--you)"
                />
                <StatTile
                  value={`${stats.games_won}W / ${stats.games_played - stats.games_won}L`}
                  label="Record"
                  color="var(--ink-text)"
                />
              </div>

              {/* Second row: 2 columns for avg stats */}
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                <StatTile
                  value={stats.avg_turns.toFixed(1)}
                  label="Avg Turns"
                  color="var(--ink-text)"
                />
                <StatTile
                  value={
                    stats.avg_game_duration_seconds < 60
                      ? `${Math.round(stats.avg_game_duration_seconds)}s`
                      : `${Math.floor(stats.avg_game_duration_seconds / 60)}m ${Math.round(stats.avg_game_duration_seconds % 60)}s`
                  }
                  label="Avg Game"
                  color="var(--ink-text)"
                />
              </div>

              {/* Card Stats */}
              {stats.card_stats && stats.card_stats.length > 0 && (
                <div>
                  <h3
                    style={{
                      fontFamily: 'var(--font-card-name)',
                      fontSize: '20px',
                      color: 'var(--ink-text)',
                      marginBottom: 'var(--spacing-component-sm)',
                    }}
                  >
                    Card Usage
                  </h3>

                  {/* Column Headers */}
                  <div
                    className="flex items-center"
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
                      style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', minWidth: 0 }}
                    >
                      Card{getSortIndicator('card_name')}
                    </button>
                    <button
                      onClick={() => handleSort('games_won')}
                      style={{ width: '56px', textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', flexShrink: 0 }}
                    >
                      Wins{getSortIndicator('games_won')}
                    </button>
                    <button
                      onClick={() => handleSort('games_lost')}
                      style={{ width: '56px', textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', flexShrink: 0 }}
                    >
                      Loss{getSortIndicator('games_lost')}
                    </button>
                    <button
                      onClick={() => handleSort('win_rate')}
                      style={{ width: '56px', textAlign: 'center', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', flexShrink: 0 }}
                    >
                      Rate{getSortIndicator('win_rate')}
                    </button>
                  </div>

                  <div className="flex flex-col overflow-y-auto overflow-x-hidden" style={{ maxHeight: '192px' }}>
                    {getSortedCardStats(stats.card_stats).map((card: CardStats) => {
                      const gamesLost = card.games_played - card.games_won;
                      return (
                        <div
                          key={card.card_name}
                          className="flex items-center"
                          style={{
                            gap: 'var(--spacing-component-sm)',
                            padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                            background: heatmapBg(card.win_rate),
                          }}
                        >
                          <div className="flex-1 min-w-0" style={{ fontWeight: 700, color: 'var(--ink-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {card.card_name}
                          </div>
                          <div style={{ width: '56px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)' }}>
                            {card.games_won}
                          </div>
                          <div style={{ width: '56px', flexShrink: 0, textAlign: 'center', fontSize: '13px', color: 'var(--ink-faint)' }}>
                            {gamesLost}
                          </div>
                          <div style={{ width: '56px', flexShrink: 0, textAlign: 'center', fontWeight: 900, color: winRateColor(card.win_rate) }}>
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

function StatTile({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div
      className="text-center"
      style={{
        padding: 'var(--spacing-component-sm)',
        background: 'rgba(0,0,0,.25)',
        borderRadius: '8px',
      }}
    >
      <div style={{ fontSize: '22px', fontWeight: 900, color }}>{value}</div>
      <div style={{ fontSize: '11px', color: 'var(--ink-faint)' }}>{label}</div>
    </div>
  );
}

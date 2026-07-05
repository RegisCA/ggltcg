/**
 * Leaderboard Component
 * Displays top players ranked by wins - losses differential.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — no
 * mockup exists for this screen, so this applies the established language:
 * dark panel with gold hairline border, Gochi Hand title, --you highlighting
 * for the viewing player's row (viewer-relative, same idiom as VictoryScreen).
 *
 * Decorative emoji removed per §8 (🏆🎲😢🎮🥇🥈🥉🔥); ranks render as plain
 * numerals — none of these are content-bearing state badges.
 */

import { useState, useEffect } from 'react';
import { getLeaderboard } from '../api/statsService';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { useAuth } from '../contexts/AuthContext';
import type { LeaderboardResponse, LeaderboardEntry } from '../types/api';

interface LeaderboardProps {
  onClose: () => void;
  onViewPlayer?: (playerId: string) => void;
  /** Test/preview seam: when provided, skips the getLeaderboard() fetch and
   *  renders this canned list instead. Production callers never pass this —
   *  used by the /design.html#leaderboard fixture and component tests. */
  entriesOverride?: LeaderboardEntry[];
}

export function Leaderboard({ onClose, onViewPlayer, entriesOverride }: LeaderboardProps) {
  const localPlayerId = useLocalPlayerId();
  const { user } = useAuth();
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(
    entriesOverride
      ? { entries: entriesOverride, total_players: entriesOverride.length, min_games_required: 3 }
      : null
  );
  const [loading, setLoading] = useState(!entriesOverride);
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
    if (entriesOverride) return; // preview/test harness supplies entries directly
    fetchLeaderboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Leaderboard entries carry Google ids for human players. In production the
  // Leaderboard opens from LobbyHome — outside any game, so there is no
  // LocalPlayerProvider; the signed-in user is the viewer. The context id is
  // kept as a fallback for in-game mounts and the design harness.
  const viewerId = user?.google_id ?? localPlayerId;
  const isViewer = (entry: LeaderboardEntry): boolean =>
    !!viewerId && entry.player_id === viewerId;

  const winRateColor = (winRate: number): string => {
    if (winRate >= 70) return 'var(--gold)';
    if (winRate >= 50) return 'var(--ink-text)';
    return 'var(--danger)';
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
        padding: 'var(--spacing-component-md)',
      }}
    >
      <div
        className="flex flex-col"
        style={{
          width: '600px',
          maxWidth: '100%',
          maxHeight: '80vh',
          background: '#241E17',
          borderRadius: '8px',
          border: '1px solid var(--gold)',
          boxShadow: '0 8px 24px rgba(0,0,0,.4)',
        }}
      >
        {/* Header */}
        <div
          className="flex-shrink-0"
          style={{
            padding: 'var(--spacing-component-md)',
            borderBottom: '1px solid rgba(242,193,78,.25)',
          }}
        >
          <div className="flex justify-between items-start">
            <div>
              <h2 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', color: 'var(--ink-text)' }}>
                Leaderboard
              </h2>
              <p style={{ marginTop: '4px', fontSize: '14px', color: 'var(--ink-muted)' }}>
                Top players by win differential
              </p>
            </div>
            <button
              onClick={onClose}
              aria-label="Close leaderboard"
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
        </div>

        {/* Content */}
        <div className="overflow-y-auto overflow-x-hidden flex-1" style={{ padding: 'var(--spacing-component-lg)' }}>
          {loading && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0', color: 'var(--ink-muted)' }}>
              <p>Loading leaderboard...</p>
            </div>
          )}

          {error && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0' }}>
              <p style={{ color: 'var(--danger)' }}>{error}</p>
              <button
                onClick={fetchLeaderboard}
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
                Retry
              </button>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length === 0 && (
            <div className="text-center" style={{ padding: 'var(--spacing-component-xl) 0', color: 'var(--ink-muted)' }}>
              <p>No players on the leaderboard yet!</p>
              <p style={{ marginTop: 'var(--spacing-component-xs)', fontSize: '13px', color: 'var(--ink-faint)' }}>
                Play some games to be the first!
              </p>
            </div>
          )}

          {!loading && !error && leaderboard && leaderboard.entries.length > 0 && (
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              {leaderboard.entries.map((entry: LeaderboardEntry) => {
                const you = isViewer(entry);
                return (
                  <div
                    key={entry.player_id}
                    onClick={() => onViewPlayer?.(entry.player_id)}
                    data-testid={`leaderboard-row-${entry.player_id}`}
                    className={onViewPlayer ? 'cursor-pointer' : ''}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      minWidth: 0,
                      gap: 'var(--spacing-component-sm)',
                      padding: 'var(--spacing-component-sm) var(--spacing-component-md)',
                      borderRadius: '6px',
                      background: you ? 'rgba(126,166,224,.14)' : 'rgba(237,232,222,.04)',
                      border: `1px solid ${you ? 'var(--you)' : 'rgba(237,232,222,.1)'}`,
                    }}
                  >
                    {/* Rank */}
                    <div
                      style={{
                        width: '28px',
                        flexShrink: 0,
                        textAlign: 'center',
                        fontWeight: 900,
                        fontSize: '16px',
                        color: entry.rank <= 3 ? 'var(--gold)' : 'var(--ink-faint)',
                      }}
                    >
                      {entry.rank}
                    </div>

                    {/* Player Info */}
                    <div className="flex-1 min-w-0">
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: '15px',
                          color: you ? 'var(--you)' : 'var(--ink-text)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {entry.display_name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--ink-faint)' }}>
                        {entry.games_won}W / {entry.games_played - entry.games_won}L
                      </div>
                    </div>

                    {/* Win Rate */}
                    <div style={{ flexShrink: 0, textAlign: 'right' }}>
                      <div style={{ fontWeight: 900, fontSize: '16px', color: winRateColor(entry.win_rate) }}>
                        {entry.win_rate.toFixed(1)}%
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--ink-faint)', whiteSpace: 'nowrap' }}>
                        {entry.games_played} games
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!loading && !error && leaderboard && (
          <div
            className="text-center flex-shrink-0"
            style={{
              padding: 'var(--spacing-component-md)',
              borderTop: '1px solid rgba(237,232,222,.12)',
              fontSize: '12px',
              color: 'var(--ink-faint)',
            }}
          >
            Minimum {leaderboard.min_games_required} game{leaderboard.min_games_required !== 1 ? 's' : ''} required to qualify
          </div>
        )}
      </div>
    </div>
  );
}

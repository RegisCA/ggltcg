/**
 * Smoke test for PlayerStats: renders canned stats via the statsOverride
 * seam (same seam the /design.html#player-stats fixture uses) without
 * fetching, and applies viewer-relative --you highlighting to the player's
 * own name when they are the viewer.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlayerStats } from '../PlayerStats';
import { LocalPlayerProvider } from '../../contexts/LocalPlayerContext';
import { AuthProvider } from '../../contexts/AuthContext';
import type { PlayerStats as PlayerStatsType } from '../../types/api';

const STATS: PlayerStatsType = {
  player_id: 'viewer',
  display_name: 'Régis',
  games_played: 20,
  games_won: 14,
  win_rate: 70.0,
  total_tussles: 58,
  tussles_won: 34,
  tussle_win_rate: 58.6,
  avg_turns: 8.4,
  avg_game_duration_seconds: 312,
  card_stats: [
    { card_name: 'Knight', games_played: 14, games_won: 11, win_rate: 78.6 },
    { card_name: 'Archer', games_played: 5, games_won: 1, win_rate: 20.0 },
  ],
};

describe('PlayerStats', () => {
  it('renders canned stats from statsOverride without fetching', () => {
    render(
      <AuthProvider>
        <PlayerStats playerId="viewer" onClose={vi.fn()} statsOverride={STATS} />
      </AuthProvider>
    );

    expect(screen.getByText('Régis')).toBeInTheDocument();
    expect(screen.getByText('70.0%')).toBeInTheDocument();
    expect(screen.getByText('Knight')).toBeInTheDocument();
    expect(screen.getByText('Archer')).toBeInTheDocument();
  });

  it("highlights the player's name when they are the local viewer", () => {
    render(
      <AuthProvider>
        <LocalPlayerProvider value="viewer">
          <PlayerStats playerId="viewer" onClose={vi.fn()} statsOverride={STATS} />
        </LocalPlayerProvider>
      </AuthProvider>
    );

    const name = screen.getByText('Régis');
    expect(name.style.color).toContain('var(--you)');
  });
});

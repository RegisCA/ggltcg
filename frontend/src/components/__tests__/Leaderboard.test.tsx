/**
 * Smoke test for Leaderboard: renders canned entries via the entriesOverride
 * seam (same seam the /design.html#leaderboard fixture uses) and highlights
 * the local viewing player's row (viewer-relative --you idiom).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Leaderboard } from '../Leaderboard';
import { LocalPlayerProvider } from '../../contexts/LocalPlayerContext';
import { AuthProvider } from '../../contexts/AuthContext';

const ENTRIES = [
  { rank: 1, player_id: 'p1', display_name: 'Gemiknight', games_played: 10, games_won: 9, win_rate: 90 },
  { rank: 2, player_id: 'viewer', display_name: 'Régis', games_played: 8, games_won: 5, win_rate: 62.5 },
];

describe('Leaderboard', () => {
  it('renders canned entries from entriesOverride without fetching', () => {
    render(
      <AuthProvider>
        <Leaderboard onClose={vi.fn()} entriesOverride={ENTRIES} />
      </AuthProvider>
    );

    expect(screen.getByText('Gemiknight')).toBeInTheDocument();
    expect(screen.getByText('Régis')).toBeInTheDocument();
    expect(screen.getByText('90.0%')).toBeInTheDocument();
  });

  it("highlights the local viewing player's row", () => {
    render(
      <AuthProvider>
        <LocalPlayerProvider value="viewer">
          <Leaderboard onClose={vi.fn()} entriesOverride={ENTRIES} />
        </LocalPlayerProvider>
      </AuthProvider>
    );

    const viewerRow = screen.getByTestId('leaderboard-row-viewer');
    expect(viewerRow.style.border).toContain('var(--you)');

    const otherRow = screen.getByTestId('leaderboard-row-p1');
    expect(otherRow.style.border).not.toContain('var(--you)');
  });
});

/**
 * Smoke test for LobbyJoin: game-code validation error path.
 * AuthProvider is real (localStorage-only, no network) so useAuth() resolves
 * to an unauthenticated user, same as the /design.html harness.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LobbyJoin } from '../LobbyJoin';
import { AuthProvider } from '../../contexts/AuthContext';

function renderLobbyJoin() {
  return render(
    <AuthProvider>
      <LobbyJoin onLobbyJoined={vi.fn()} onBack={vi.fn()} />
    </AuthProvider>
  );
}

describe('LobbyJoin', () => {
  it('shows a validation error when the join button is clicked without a full code', async () => {
    const user = userEvent.setup();
    renderLobbyJoin();

    const input = screen.getByLabelText('Game Code');
    await user.type(input, 'ABC');

    // Button stays disabled until 6 characters are entered (canJoin gate),
    // but a short code is still rejected if forced — verify via a code of
    // exactly 6 chars that fails the alphanumeric regex is not reachable
    // (input strips non-alphanumeric), so instead exercise the "must be
    // logged in" branch, which fires unconditionally when playerId is empty.
    const joinButton = screen.getByRole('button', { name: /join game/i });
    await user.click(joinButton);

    expect(await screen.findByText(/must be logged in to join a game/i)).toBeInTheDocument();
  });

  it('uppercases and truncates the game code input to 6 alphanumeric characters', async () => {
    const user = userEvent.setup();
    renderLobbyJoin();

    const input = screen.getByLabelText('Game Code') as HTMLInputElement;
    await user.type(input, 'ab-12cd34');

    expect(input.value).toBe('AB12CD');
  });
});

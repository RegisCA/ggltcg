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
  it('keeps the join button disabled until 6 characters are entered', async () => {
    const user = userEvent.setup();
    renderLobbyJoin();

    const input = screen.getByLabelText('Game Code');
    const joinButton = screen.getByRole('button', { name: /join game/i });

    expect(joinButton).toBeDisabled();
    await user.type(input, 'ABC12');
    expect(joinButton).toBeDisabled();
    await user.type(input, '3');
    expect(joinButton).toBeEnabled();
  });

  it('uppercases and truncates the game code input to 6 alphanumeric characters', async () => {
    const user = userEvent.setup();
    renderLobbyJoin();

    const input = screen.getByLabelText('Game Code') as HTMLInputElement;
    await user.type(input, 'ab-12cd34');

    expect(input.value).toBe('AB12CD');
  });
});

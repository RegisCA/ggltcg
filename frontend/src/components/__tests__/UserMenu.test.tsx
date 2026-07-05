/**
 * Smoke test for UserMenu: the sign-out callback fires when the user
 * confirms the logout dialog.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserMenu } from '../UserMenu';
import { AuthProvider } from '../../contexts/AuthContext';

const TOKEN_KEY = 'ggltcg_auth_token';
const USER_KEY = 'ggltcg_user';

const FAKE_USER = {
  google_id: 'test-google-id',
  first_name: 'Régis',
  display_name: 'Régis',
  custom_display_name: null,
};

function seedAuth() {
  const fakeJwt = `fixture.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.sig`;
  localStorage.setItem(TOKEN_KEY, fakeJwt);
  localStorage.setItem(USER_KEY, JSON.stringify(FAKE_USER));
}

describe('UserMenu', () => {
  beforeEach(() => {
    seedAuth();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('fires logout when sign-out is confirmed', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <UserMenu />
      </AuthProvider>
    );

    // Wait for the auth provider to hydrate from localStorage.
    expect(await screen.findByText('Régis')).toBeInTheDocument();

    await user.click(screen.getByText('Régis'));
    await user.click(await screen.findByText('Logout'));

    expect(window.confirm).toHaveBeenCalled();
    // logout() clears localStorage; the menu button disappears since user becomes null.
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

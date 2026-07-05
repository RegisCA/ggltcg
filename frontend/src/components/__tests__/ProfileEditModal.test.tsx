/**
 * Smoke test for ProfileEditModal: renders the current display name and
 * disables Save when the name exceeds validation limits.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProfileEditModal } from '../ProfileEditModal';
import { AuthProvider } from '../../contexts/AuthContext';

const TOKEN_KEY = 'ggltcg_auth_token';
const USER_KEY = 'ggltcg_user';

const FAKE_USER = {
  google_id: 'test-google-id',
  first_name: 'Régis',
  display_name: 'Régis',
  custom_display_name: 'Reggie',
};

function seedAuth() {
  const fakeJwt = `fixture.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.sig`;
  localStorage.setItem(TOKEN_KEY, fakeJwt);
  localStorage.setItem(USER_KEY, JSON.stringify(FAKE_USER));
}

describe('ProfileEditModal', () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders the current display name and an enabled Save button', async () => {
    seedAuth();
    render(
      <AuthProvider>
        <ProfileEditModal isOpen={true} onClose={vi.fn()} />
      </AuthProvider>
    );

    const input = await screen.findByLabelText('Display Name');
    expect(input).toHaveValue('Reggie');
    expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled();
  });

  it('updates the character counter as the name changes', async () => {
    seedAuth();
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <ProfileEditModal isOpen={true} onClose={vi.fn()} />
      </AuthProvider>
    );

    const input = await screen.findByLabelText('Display Name');
    await user.clear(input);
    await user.type(input, 'Newname');
    expect(screen.getByText('7/50 characters')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled();
  });

  it('does not render when closed', () => {
    seedAuth();
    render(
      <AuthProvider>
        <ProfileEditModal isOpen={false} onClose={vi.fn()} />
      </AuthProvider>
    );
    expect(screen.queryByText('Edit Profile')).not.toBeInTheDocument();
  });
});

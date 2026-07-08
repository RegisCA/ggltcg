/**
 * Tests for PR A6: the admin.html sign-in gate.
 *
 * Covers the three states a visitor can land in: no token (sign-in
 * screen), a token that isn't on the backend's admin allowlist (403 ->
 * "Not Authorized"), and an allowlisted token (renders AdminApp). Does
 * not re-test AdminApp's own internals (covered in tabs.test.tsx etc.) --
 * AdminApp is mocked to a stub so this file stays focused on the gate's
 * own branching logic.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminAuthGate from '../AdminAuthGate';
import { authService } from '../../../api/authService';
import { getAdminSummary } from '../../../api/adminService';

const TOKEN_KEY = 'ggltcg_auth_token';
const USER_KEY = 'ggltcg_user';

vi.mock('../../../api/adminService', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getAdminSummary: vi.fn(),
}));

vi.mock('../../../api/authService', () => ({
  authService: {
    authenticateWithGoogle: vi.fn(),
  },
}));

vi.mock('../AdminApp', () => ({
  default: () => <div>Stub AdminApp Content</div>,
}));

vi.mock('@react-oauth/google', () => ({
  GoogleLogin: ({ onSuccess }: { onSuccess: (c: { credential: string }) => void }) => (
    <button onClick={() => onSuccess({ credential: 'fake-google-credential' })}>
      Mock Google Sign In
    </button>
  ),
}));

function makeAxiosError(status: number) {
  const error = new Error('request failed') as Error & { response: { status: number } };
  error.response = { status };
  return error;
}

const renderGate = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AdminAuthGate />
    </QueryClientProvider>
  );
};

describe('AdminAuthGate', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(getAdminSummary).mockReset();
    vi.mocked(authService.authenticateWithGoogle).mockReset();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('shows the sign-in screen when no token is stored, without calling the admin API', () => {
    renderGate();
    expect(screen.getByText('GGLTCG Admin')).toBeInTheDocument();
    expect(getAdminSummary).not.toHaveBeenCalled();
  });

  it('stores the token/user and moves past sign-in on a successful Google login', async () => {
    vi.mocked(authService.authenticateWithGoogle).mockResolvedValue({
      jwt_token: 'new-jwt',
      user: { google_id: 'gid', first_name: 'Régis', display_name: 'Régis', custom_display_name: null },
    });
    vi.mocked(getAdminSummary).mockImplementation(() => new Promise(() => {})); // stay loading

    renderGate();
    fireEvent.click(screen.getByText('Mock Google Sign In'));

    await waitFor(() => expect(localStorage.getItem(TOKEN_KEY)).toBe('new-jwt'));
    expect(JSON.parse(localStorage.getItem(USER_KEY)!).display_name).toBe('Régis');
  });

  it('renders "Not Authorized" with the signed-in user\'s name on a 403, and sign-out clears storage', async () => {
    localStorage.setItem(TOKEN_KEY, 'existing-jwt');
    localStorage.setItem(
      USER_KEY,
      JSON.stringify({ google_id: 'gid', first_name: 'Bob', display_name: 'Bob', custom_display_name: null })
    );
    vi.mocked(getAdminSummary).mockRejectedValue(makeAxiosError(403));

    renderGate();

    await screen.findByText('Not Authorized');
    expect(screen.getByText(/Signed in as Bob/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Sign out and try a different account'));

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    await screen.findByText('GGLTCG Admin');
  });

  it('renders AdminApp once the summary call succeeds (allowlisted)', async () => {
    localStorage.setItem(TOKEN_KEY, 'existing-jwt');
    localStorage.setItem(USER_KEY, JSON.stringify({ google_id: 'gid', first_name: 'Régis' }));
    vi.mocked(getAdminSummary).mockResolvedValue({
      users: { total: 1 },
      games: { total: 1, active: 0, completed: 1, recent_24h: 0 },
      ai_logs: { total: 0, recent_1h: 0 },
      playbacks: { total: 0 },
    });

    renderGate();

    await screen.findByText('Stub AdminApp Content');
  });

  it('falls back to the sign-in screen on a 401 (invalid/expired token) and clears storage', async () => {
    localStorage.setItem(TOKEN_KEY, 'stale-jwt');
    localStorage.setItem(USER_KEY, JSON.stringify({ google_id: 'gid', first_name: 'Régis' }));
    vi.mocked(getAdminSummary).mockRejectedValue(makeAxiosError(401));

    renderGate();

    await screen.findByText('GGLTCG Admin');
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

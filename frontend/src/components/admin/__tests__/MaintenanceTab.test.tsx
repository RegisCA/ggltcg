/**
 * Tests for MaintenanceTab covering its three states: no key entered,
 * stats loaded for a valid key, and an invalid key clearing back to the
 * entry form. maintenanceService is mocked; sessionStorage is reset
 * between tests so no real key material persists.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MaintenanceTab from '../tabs/MaintenanceTab';
import { getMaintenanceStats, runCleanup } from '../../../api/maintenanceService';

vi.mock('../../../api/maintenanceService', () => ({
  getMaintenanceStats: vi.fn(),
  runCleanup: vi.fn(),
}));

const mockGetStats = getMaintenanceStats as unknown as ReturnType<typeof vi.fn>;
const mockRunCleanup = runCleanup as unknown as ReturnType<typeof vi.fn>;

const STORAGE_KEY = 'ggltcg_maintenance_key';

const renderTab = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MaintenanceTab />
    </QueryClientProvider>
  );
};

const STATS = {
  active_games_total: 5,
  active_games_stale: 1,
  ai_logs_total: 100,
  ai_logs_stale: 10,
  playback_total: 20,
  playback_stale: 2,
  simulations_total: 3,
  simulations_stale: 1,
};

describe('MaintenanceTab', () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockGetStats.mockReset();
    mockRunCleanup.mockReset();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('shows the key entry form when no key is stored', () => {
    renderTab();
    expect(screen.getByLabelText('Maintenance API key')).toBeInTheDocument();
    expect(screen.queryByText('Run Cleanup')).not.toBeInTheDocument();
  });

  it('loads stats once a key is submitted', async () => {
    mockGetStats.mockResolvedValueOnce(STATS);
    const user = userEvent.setup();
    renderTab();

    await user.type(screen.getByLabelText('Maintenance API key'), 'a-fake-test-key');
    await user.click(screen.getByRole('button', { name: 'Submit' }));

    await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument());
    expect(screen.getByText('1 stale (> 24h)')).toBeInTheDocument();
    expect(mockGetStats).toHaveBeenCalledWith('a-fake-test-key');
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe('a-fake-test-key');
  });

  it('clears the key and shows an invalid-key message on a 401/403', async () => {
    sessionStorage.setItem(STORAGE_KEY, 'a-stale-test-key');
    mockGetStats.mockRejectedValueOnce({ response: { status: 403 } });
    renderTab();

    await waitFor(() => expect(screen.getByText('Invalid API key. Please try again.')).toBeInTheDocument());
    expect(screen.getByLabelText('Maintenance API key')).toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

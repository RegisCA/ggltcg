/**
 * Verifies the useRunStatus polling hook (PR A2 modernization of the old
 * manual setInterval): it refetches on the 3s cadence while a run is in
 * progress and stops polling once the status is terminal.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRunStatus, isTerminalRunStatus } from '../useSimulationRuns';
import { getRunStatus } from '../../api/simulationService';

vi.mock('../../api/simulationService', () => ({
  getRunStatus: vi.fn(),
}));

const mockGetRunStatus = vi.mocked(getRunStatus);

const status = (s: string) => ({
  run_id: 1,
  status: s,
  total_games: 10,
  completed_games: s === 'completed' ? 10 : 5,
  error_message: null,
});

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('isTerminalRunStatus', () => {
  it('treats completed/failed/cancelled as terminal', () => {
    expect(isTerminalRunStatus('completed')).toBe(true);
    expect(isTerminalRunStatus('failed')).toBe(true);
    expect(isTerminalRunStatus('cancelled')).toBe(true);
    expect(isTerminalRunStatus('running')).toBe(false);
    expect(isTerminalRunStatus('pending')).toBe(false);
    expect(isTerminalRunStatus(undefined)).toBe(false);
  });
});

describe('useRunStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('does not fetch when there is no active run', () => {
    renderHook(() => useRunStatus(null), { wrapper: createWrapper() });
    expect(mockGetRunStatus).not.toHaveBeenCalled();
  });

  it('polls every 3s while running, then stops once the run is terminal', async () => {
    mockGetRunStatus
      .mockResolvedValueOnce(status('running'))
      .mockResolvedValue(status('completed'));

    const { result } = renderHook(() => useRunStatus(1), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.data?.status).toBe('running'));
    expect(mockGetRunStatus).toHaveBeenCalledTimes(1);

    // First interval tick: refetch returns terminal status
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    await waitFor(() => expect(result.current.data?.status).toBe('completed'));
    expect(mockGetRunStatus).toHaveBeenCalledTimes(2);

    // Terminal status: refetchInterval is false, no further polling
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(mockGetRunStatus).toHaveBeenCalledTimes(2);
  });
});

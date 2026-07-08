/**
 * Verifies the useRunStatus polling hook (PR A2 modernization of the old
 * manual setInterval): it refetches on the 3s cadence while a run is in
 * progress and stops polling once the status is terminal.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRunStatus, isTerminalRunStatus, isSlowRunStatus, useResumeRun, usePauseRun } from '../useSimulationRuns';
import { getRunStatus, resumeRun, pauseRun } from '../../api/simulationService';

vi.mock('../../api/simulationService', () => ({
  getRunStatus: vi.fn(),
  resumeRun: vi.fn(),
  pauseRun: vi.fn(),
}));

const mockGetRunStatus = vi.mocked(getRunStatus);
const mockResumeRun = vi.mocked(resumeRun);
const mockPauseRun = vi.mocked(pauseRun);

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

describe('isSlowRunStatus', () => {
  it('treats paused/budget_exhausted as slow, everything else as not', () => {
    expect(isSlowRunStatus('paused')).toBe(true);
    expect(isSlowRunStatus('budget_exhausted')).toBe(true);
    expect(isSlowRunStatus('running')).toBe(false);
    expect(isSlowRunStatus('completed')).toBe(false);
    expect(isSlowRunStatus(undefined)).toBe(false);
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

  it('slows to a 30s cadence once the run is paused', async () => {
    mockGetRunStatus
      .mockResolvedValueOnce(status('running'))
      .mockResolvedValue(status('paused'));

    const { result } = renderHook(() => useRunStatus(1), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.data?.status).toBe('running'));
    expect(mockGetRunStatus).toHaveBeenCalledTimes(1);

    // Running -> 3s tick brings back paused
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    await waitFor(() => expect(result.current.data?.status).toBe('paused'));
    expect(mockGetRunStatus).toHaveBeenCalledTimes(2);

    // A further 3s should NOT trigger another fetch (now on the 30s cadence)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(mockGetRunStatus).toHaveBeenCalledTimes(2);

    // Advancing to 30s total (27s more) does trigger the next poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(27000);
    });
    await waitFor(() => expect(mockGetRunStatus).toHaveBeenCalledTimes(3));
  });
});

describe('useResumeRun / usePauseRun', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('calls resumeRun with the run id', async () => {
    mockResumeRun.mockResolvedValue(undefined);
    const { result } = renderHook(() => useResumeRun(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync(42);
    });

    expect(mockResumeRun).toHaveBeenCalledWith(42);
  });

  it('calls pauseRun with the run id', async () => {
    mockPauseRun.mockResolvedValue(undefined);
    const { result } = renderHook(() => usePauseRun(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync(7);
    });

    expect(mockPauseRun).toHaveBeenCalledWith(7);
  });

  it('surfaces a 409 error from resumeRun to the caller', async () => {
    mockResumeRun.mockRejectedValue({ response: { status: 409, data: { detail: 'already resumed' } } });
    const { result } = renderHook(() => useResumeRun(), { wrapper: createWrapper() });

    await expect(result.current.mutateAsync(1)).rejects.toBeTruthy();
  });
});

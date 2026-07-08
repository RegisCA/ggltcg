/**
 * Regression test for PR A6: a 401/403 from an admin data query must settle
 * into isError immediately, with no retry. Retrying an auth failure is never
 * correct, and AdminAuthGate's admin-access check (built on useSummary())
 * depends on this settling fast rather than sitting through a retry cycle.
 *
 * Uses a QueryClient with a generous default retry count (3) so a passing
 * test proves the per-hook `retry: shouldRetry` override is what's actually
 * suppressing the retry -- not just an accidental global retry:false.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSummary } from '../useAdminData';
import { getAdminSummary } from '../../api/adminService';

vi.mock('../../api/adminService', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getAdminSummary: vi.fn(),
}));

const mockGetAdminSummary = vi.mocked(getAdminSummary);

function makeAxiosError(status: number) {
  const error = new Error('request failed') as Error & { response: { status: number } };
  error.response = { status };
  return error;
}

const createWrapper = () => {
  // Deliberately NOT retry:false -- a generous default so the test proves
  // the per-hook override, not an accidental global suppression.
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 3 } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useSummary retry behavior', () => {
  beforeEach(() => {
    mockGetAdminSummary.mockReset();
  });

  it('does not retry on 403 and settles into isError with a single call', async () => {
    mockGetAdminSummary.mockRejectedValue(makeAxiosError(403));

    const { result } = renderHook(() => useSummary(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockGetAdminSummary).toHaveBeenCalledTimes(1);
  });

  it('does not retry on 401 and settles into isError with a single call', async () => {
    mockGetAdminSummary.mockRejectedValue(makeAxiosError(401));

    const { result } = renderHook(() => useSummary(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockGetAdminSummary).toHaveBeenCalledTimes(1);
  });

  it('still retries once on a non-auth error (e.g. a transient 500)', async () => {
    mockGetAdminSummary.mockRejectedValue(makeAxiosError(500));

    const { result } = renderHook(() => useSummary(), { wrapper: createWrapper() });

    // Genuine retries wait out the ~1s default backoff between attempts.
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 });
    expect(mockGetAdminSummary.mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});

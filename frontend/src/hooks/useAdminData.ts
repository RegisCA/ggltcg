/**
 * TanStack Query hooks backing the Admin Data Viewer tabs.
 *
 * Wraps the useQuery calls moved out of AdminDataViewer.tsx (PR A2) —
 * query keys, refetch intervals, and enabled conditions are preserved
 * exactly. Each hook takes an `isActive` flag where the original refetch
 * interval depended on the active tab.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getAdminSummary,
  getAiLogs,
  getAdminGames,
  getGamePlaybacks,
  getAdminUsers,
} from '../api/adminService';
import type { SummaryStats } from '../components/admin/types';

/**
 * A 401/403 means the session is unauthenticated/unauthorized, not a
 * transient failure -- retrying it is never correct (and AdminAuthGate's
 * admin-access check depends on this settling into `isError` immediately
 * rather than sitting through a retry backoff).
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 401 || status === 403) return false;
  return failureCount < 1;
}

// Fetch summary stats
export function useSummary() {
  return useQuery<SummaryStats>({
    queryKey: ['admin-summary'],
    queryFn: getAdminSummary,
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: shouldRetry,
  });
}

// Fetch AI logs
export function useAiLogs(gameIdFilter: string | null, isActive: boolean) {
  return useQuery({
    queryKey: ['admin-ai-logs', gameIdFilter],
    queryFn: () => getAiLogs({ limit: 100, gameId: gameIdFilter }),
    refetchInterval: isActive ? 10000 : 30000, // Faster refresh when viewing
    retry: shouldRetry,
  });
}

// Fetch AI logs for the selected playback (for metrics/symptoms)
export function usePlaybackAiLogs(gameId: string | undefined) {
  return useQuery({
    queryKey: ['admin-ai-logs-for-playback', gameId],
    queryFn: async () => {
      if (!gameId) return { count: 0, logs: [] };
      return getAiLogs({ limit: 200, gameId });
    },
    enabled: !!gameId,
    refetchInterval: false,
  });
}

// Fetch games
export function useGames(isActive: boolean) {
  return useQuery({
    queryKey: ['admin-games'],
    queryFn: () => getAdminGames(50),
    refetchInterval: isActive ? 10000 : 30000,
    retry: shouldRetry,
  });
}

// Fetch playbacks
export function usePlaybacks(isActive: boolean) {
  return useQuery({
    queryKey: ['admin-playbacks'],
    queryFn: () => getGamePlaybacks(30),
    refetchInterval: isActive ? 10000 : 30000,
    retry: shouldRetry,
  });
}

// Fetch users
export function useUsers(isActive: boolean) {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: () => getAdminUsers(50),
    refetchInterval: isActive ? 10000 : 30000,
    retry: shouldRetry,
  });
}

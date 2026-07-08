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

// Fetch summary stats
export function useSummary() {
  return useQuery<SummaryStats>({
    queryKey: ['admin-summary'],
    queryFn: getAdminSummary,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

// Fetch AI logs
export function useAiLogs(gameIdFilter: string | null, isActive: boolean) {
  return useQuery({
    queryKey: ['admin-ai-logs', gameIdFilter],
    queryFn: () => getAiLogs({ limit: 100, gameId: gameIdFilter }),
    refetchInterval: isActive ? 10000 : 30000, // Faster refresh when viewing
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
  });
}

// Fetch playbacks
export function usePlaybacks(isActive: boolean) {
  return useQuery({
    queryKey: ['admin-playbacks'],
    queryFn: () => getGamePlaybacks(30),
    refetchInterval: isActive ? 10000 : 30000,
  });
}

// Fetch users
export function useUsers(isActive: boolean) {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: () => getAdminUsers(50),
    refetchInterval: isActive ? 10000 : 30000,
  });
}

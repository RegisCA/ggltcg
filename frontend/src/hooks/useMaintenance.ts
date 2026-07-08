/**
 * TanStack Query hooks backing the admin Maintenance tab.
 *
 * Stats are only fetched once an API key is present (the key lives in
 * sessionStorage, held by the tab component). Cleanup invalidates the
 * stats query so the tab reflects the post-cleanup counts.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMaintenanceStats, runCleanup } from '../api/maintenanceService';
import type { MaintenanceStats, CleanupResult } from '../api/maintenanceService';

export function useMaintenanceStats(apiKey: string | null) {
  return useQuery<MaintenanceStats>({
    queryKey: ['maintenance-stats', apiKey],
    queryFn: () => getMaintenanceStats(apiKey!),
    enabled: !!apiKey,
    retry: false,
  });
}

export function useRunCleanup(apiKey: string | null) {
  const queryClient = useQueryClient();
  return useMutation<CleanupResult, unknown, void>({
    mutationFn: () => runCleanup(apiKey!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maintenance-stats', apiKey] });
    },
  });
}

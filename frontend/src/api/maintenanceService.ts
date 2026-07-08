/**
 * Maintenance API service functions
 * API calls for the maintenance endpoints (/maintenance/*), which back the
 * scheduled GitHub Actions cleanup job. Both endpoints require an
 * X-API-Key header matching the backend's MAINTENANCE_API_KEY env var.
 */

import { apiClient } from './client';

export interface MaintenanceStats {
  active_games_total: number;
  active_games_stale: number; // active but not updated in 24h
  ai_logs_total: number;
  ai_logs_stale: number; // older than 6 hours
  playback_total: number;
  playback_stale: number; // older than 24 hours
  simulations_total: number;
  simulations_stale: number; // older than 7 days
}

export interface CleanupResult {
  games_abandoned: number;
  ai_logs_deleted: number;
  playback_deleted: number;
  simulations_deleted: number;
  execution_time_ms: number;
}

/**
 * Get current cleanup stats (totals vs stale counts) without performing cleanup.
 */
export async function getMaintenanceStats(apiKey: string): Promise<MaintenanceStats> {
  const response = await apiClient.get<MaintenanceStats>('/maintenance/stats', {
    headers: { 'X-API-Key': apiKey },
  });
  return response.data;
}

/**
 * Run the cleanup job (abandons stale games, deletes stale AI logs/playbacks/simulations).
 */
export async function runCleanup(apiKey: string): Promise<CleanupResult> {
  const response = await apiClient.post<CleanupResult>(
    '/maintenance/cleanup',
    undefined,
    { headers: { 'X-API-Key': apiKey } }
  );
  return response.data;
}

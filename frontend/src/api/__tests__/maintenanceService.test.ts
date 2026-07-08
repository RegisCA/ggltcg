/**
 * Unit tests for maintenanceService — verifies each function hits the
 * expected endpoint and sends the X-API-Key header, with apiClient mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../client';
import { getMaintenanceStats, runCleanup } from '../maintenanceService';

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = apiClient.get as unknown as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as unknown as ReturnType<typeof vi.fn>;

const FAKE_KEY = 'test-key-placeholder';

describe('maintenanceService', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it('getMaintenanceStats fetches stats with the X-API-Key header', async () => {
    const data = {
      active_games_total: 5,
      active_games_stale: 1,
      ai_logs_total: 100,
      ai_logs_stale: 10,
      playback_total: 20,
      playback_stale: 2,
      simulations_total: 3,
      simulations_stale: 1,
    };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getMaintenanceStats(FAKE_KEY);

    expect(mockGet).toHaveBeenCalledWith('/maintenance/stats', {
      headers: { 'X-API-Key': FAKE_KEY },
    });
    expect(result).toEqual(data);
  });

  it('runCleanup posts with the X-API-Key header and returns deletion counts', async () => {
    const data = {
      games_abandoned: 2,
      ai_logs_deleted: 5,
      playback_deleted: 1,
      simulations_deleted: 0,
      execution_time_ms: 42,
    };
    mockPost.mockResolvedValueOnce({ data });

    const result = await runCleanup(FAKE_KEY);

    expect(mockPost).toHaveBeenCalledWith('/maintenance/cleanup', undefined, {
      headers: { 'X-API-Key': FAKE_KEY },
    });
    expect(result).toEqual(data);
  });
});

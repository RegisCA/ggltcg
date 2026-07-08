/**
 * Unit tests for adminService — verifies each function hits the expected
 * endpoint/params and returns the response body, with apiClient mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../client';
import {
  getAdminSummary,
  getAiLogs,
  getAdminGames,
  getGamePlaybacks,
  getPlaybackDetail,
  getAdminUsers,
} from '../adminService';

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = apiClient.get as unknown as ReturnType<typeof vi.fn>;

describe('adminService', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('getAdminSummary fetches the summary stats', async () => {
    const data = { users: { total: 1 }, games: { total: 2, active: 1, completed: 1, recent_24h: 0 }, ai_logs: { total: 0, recent_1h: 0 }, playbacks: { total: 0 } };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getAdminSummary();

    expect(mockGet).toHaveBeenCalledWith('/admin/stats/summary');
    expect(result).toEqual(data);
  });

  it('getAiLogs builds query params with limit and optional gameId', async () => {
    const data = { count: 0, logs: [] };
    mockGet.mockResolvedValueOnce({ data });

    await getAiLogs({ limit: 100 });
    expect(mockGet).toHaveBeenCalledWith('/admin/ai-logs?limit=100');

    mockGet.mockResolvedValueOnce({ data });
    await getAiLogs({ limit: 200, gameId: 'game-1' });
    expect(mockGet).toHaveBeenCalledWith('/admin/ai-logs?limit=200&game_id=game-1');
  });

  it('getAdminGames fetches with a limit', async () => {
    const data = { count: 0, games: [] };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getAdminGames(25);

    expect(mockGet).toHaveBeenCalledWith('/admin/games?limit=25');
    expect(result).toEqual(data);
  });

  it('getGamePlaybacks fetches with a limit', async () => {
    const data = { count: 0, games: [] };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getGamePlaybacks(15);

    expect(mockGet).toHaveBeenCalledWith('/admin/game-playbacks?limit=15');
    expect(result).toEqual(data);
  });

  it('getPlaybackDetail fetches a single game playback by id', async () => {
    const data = { id: 1, game_id: 'game-1' };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getPlaybackDetail('game-1');

    expect(mockGet).toHaveBeenCalledWith('/admin/game-playbacks/game-1');
    expect(result).toEqual(data);
  });

  it('getAdminUsers fetches with a limit', async () => {
    const data = { count: 0, users: [] };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getAdminUsers(10);

    expect(mockGet).toHaveBeenCalledWith('/admin/users?limit=10');
    expect(result).toEqual(data);
  });
});

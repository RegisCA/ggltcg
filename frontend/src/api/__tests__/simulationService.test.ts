/**
 * Unit tests for simulationService — verifies each function hits the
 * expected endpoint/params and returns the response body, with apiClient
 * mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../client';
import {
  getSimulationDecks,
  getSupportedModels,
  listSimulationRuns,
  startSimulation,
  getRunStatus,
  getRunResults,
  getGameDetail,
  cancelRun,
  getRunReport,
} from '../simulationService';

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = apiClient.get as unknown as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as unknown as ReturnType<typeof vi.fn>;

describe('simulationService', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it('getSimulationDecks fetches the deck list', async () => {
    const data = [{ name: 'Deck A', description: '', cards: [] }];
    mockGet.mockResolvedValueOnce({ data });

    const result = await getSimulationDecks();

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/decks');
    expect(result).toEqual(data);
  });

  it('getSupportedModels fetches the model list', async () => {
    const data = ['gemini-2.5-flash-lite'];
    mockGet.mockResolvedValueOnce({ data });

    const result = await getSupportedModels();

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/models');
    expect(result).toEqual(data);
  });

  it('listSimulationRuns fetches with a limit', async () => {
    const data: unknown[] = [];
    mockGet.mockResolvedValueOnce({ data });

    const result = await listSimulationRuns(20);

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/runs?limit=20');
    expect(result).toEqual(data);
  });

  it('startSimulation posts the config and returns run info', async () => {
    const req = {
      deck_names: ['Deck A'],
      player1_model: 'gemini-2.5-flash-lite',
      player2_model: 'gemini-2.0-flash',
      iterations_per_matchup: 10,
      max_turns: 20,
    };
    const data = { run_id: 42, total_games: 10 };
    mockPost.mockResolvedValueOnce({ data });

    const result = await startSimulation(req);

    expect(mockPost).toHaveBeenCalledWith('/admin/simulation/start', req);
    expect(result).toEqual(data);
  });

  it('getRunStatus fetches the run status', async () => {
    const data = { run_id: 42, status: 'running', total_games: 10, completed_games: 3, error_message: null };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getRunStatus(42);

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/runs/42');
    expect(result).toEqual(data);
  });

  it('getRunResults fetches full results for a run', async () => {
    const data = { run_id: 42 };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getRunResults(42);

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/runs/42/results');
    expect(result).toEqual(data);
  });

  it('getGameDetail fetches detail for one game within a run', async () => {
    const data = { game_number: 3 };
    mockGet.mockResolvedValueOnce({ data });

    const result = await getGameDetail(42, 3);

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/runs/42/games/3');
    expect(result).toEqual(data);
  });

  it('cancelRun posts a cancel request', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await cancelRun(42);

    expect(mockPost).toHaveBeenCalledWith('/admin/simulation/runs/42/cancel');
  });

  it('getRunReport fetches the plain-text report', async () => {
    const data = 'report text';
    mockGet.mockResolvedValueOnce({ data });

    const result = await getRunReport(42);

    expect(mockGet).toHaveBeenCalledWith('/admin/simulation/runs/42/report');
    expect(result).toEqual(data);
  });
});

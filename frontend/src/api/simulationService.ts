/**
 * Simulation API service functions
 * API calls for the admin simulation runner (/admin/simulation/*)
 */

import { apiClient } from './client';
import type {
  SimulationDeck,
  SimulationRun,
  SimulationResults,
  SimulationGameDetail,
} from '../components/admin/types';

export interface StartSimulationRequest {
  deck_names: string[];
  player1_model: string;
  player2_model: string;
  iterations_per_matchup: number;
  max_turns: number;
}

export interface StartSimulationResponse {
  run_id: number;
  total_games: number;
}

export interface SimulationRunStatus {
  run_id: number;
  status: string;
  total_games: number;
  completed_games: number;
  error_message: string | null;
}

/**
 * Get the available simulation decks
 */
export async function getSimulationDecks(): Promise<SimulationDeck[]> {
  const response = await apiClient.get<SimulationDeck[]>('/admin/simulation/decks');
  return response.data;
}

/**
 * Get the model names supported for simulation players
 */
export async function getSupportedModels(): Promise<string[]> {
  const response = await apiClient.get<string[]>('/admin/simulation/models');
  return response.data;
}

/**
 * List recent simulation runs
 */
export async function listSimulationRuns(limit: number = 20): Promise<SimulationRun[]> {
  const response = await apiClient.get<SimulationRun[]>(`/admin/simulation/runs?limit=${limit}`);
  return response.data;
}

/**
 * Start a new simulation run (returns immediately with a run_id; poll getRunStatus)
 */
export async function startSimulation(req: StartSimulationRequest): Promise<StartSimulationResponse> {
  const response = await apiClient.post<StartSimulationResponse>('/admin/simulation/start', req);
  return response.data;
}

/**
 * Get the current status/progress of a simulation run
 */
export async function getRunStatus(runId: number): Promise<SimulationRunStatus> {
  const response = await apiClient.get<SimulationRunStatus>(`/admin/simulation/runs/${runId}`);
  return response.data;
}

/**
 * Get full results (matchup stats + per-game summaries) for a completed run
 */
export async function getRunResults(runId: number): Promise<SimulationResults> {
  const response = await apiClient.get<SimulationResults>(`/admin/simulation/runs/${runId}/results`);
  return response.data;
}

/**
 * Get detail (charge tracking, action log) for one game within a run
 */
export async function getGameDetail(runId: number, gameNumber: number): Promise<SimulationGameDetail> {
  const response = await apiClient.get<SimulationGameDetail>(`/admin/simulation/runs/${runId}/games/${gameNumber}`);
  return response.data;
}

/**
 * Cancel an in-progress simulation run
 */
export async function cancelRun(runId: number): Promise<void> {
  await apiClient.post(`/admin/simulation/runs/${runId}/cancel`);
}

/**
 * Get the plain-text report for a completed simulation run
 */
export async function getRunReport(runId: number): Promise<string> {
  const response = await apiClient.get<string>(`/admin/simulation/runs/${runId}/report`);
  return response.data;
}

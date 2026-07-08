/**
 * TanStack Query hooks for the admin simulation runner.
 *
 * Extracted from AdminDataViewer.tsx (PR A2). The runs-list, decks, and
 * models queries are moved verbatim (same keys/intervals/enabled flags).
 *
 * The one intentional modernization of the split: the active-run progress
 * poll, previously a manual setInterval + pollErrorCountRef in the
 * component, is now a useQuery whose refetchInterval keeps the same 3s
 * cadence and stops automatically once the run reaches a terminal status
 * (completed / failed / cancelled).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getSimulationDecks,
  getSupportedModels,
  listSimulationRuns,
  startSimulation as startSimulationRequest,
  getRunStatus,
  cancelRun,
  resumeRun as resumeRunRequest,
  pauseRun as pauseRunRequest,
} from '../api/simulationService';
import type {
  StartSimulationRequest,
  SimulationRunStatus,
} from '../api/simulationService';
import type { SimulationDeck, SimulationRun } from '../components/admin/types';

export const TERMINAL_RUN_STATUSES = ['completed', 'failed', 'cancelled'] as const;

// Non-terminal but "slow": the run is parked waiting on a human/CLI resume
// (paused) or a budget window reset (budget_exhausted). Nothing is expected
// to change quickly, so these poll far less often than an actively-running
// run.
export const SLOW_RUN_STATUSES = ['paused', 'budget_exhausted'] as const;

export const isTerminalRunStatus = (status: string | undefined): boolean =>
  !!status && (TERMINAL_RUN_STATUSES as readonly string[]).includes(status);

export const isSlowRunStatus = (status: string | undefined): boolean =>
  !!status && (SLOW_RUN_STATUSES as readonly string[]).includes(status);

// Fetch simulation decks
export function useSimulationDecks(enabled: boolean) {
  return useQuery<SimulationDeck[]>({
    queryKey: ['simulation-decks'],
    queryFn: getSimulationDecks,
    enabled,
  });
}

// Fetch supported models
export function useSupportedModels(enabled: boolean) {
  return useQuery<string[]>({
    queryKey: ['simulation-models'],
    queryFn: getSupportedModels,
    enabled,
  });
}

// Fetch simulation runs
export function useSimulationRunsList(isActive: boolean) {
  return useQuery<SimulationRun[]>({
    queryKey: ['simulation-runs'],
    queryFn: () => listSimulationRuns(20),
    refetchInterval: isActive ? 5000 : 30000,
    enabled: isActive,
  });
}

/**
 * Poll the status of an in-progress run every 3 seconds (same cadence as the
 * old setInterval). Polling stops on its own once the status is terminal.
 */
export function useRunStatus(runId: number | null) {
  return useQuery<SimulationRunStatus>({
    queryKey: ['simulation-run-status', runId],
    queryFn: () => getRunStatus(runId!),
    enabled: runId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (isTerminalRunStatus(status)) return false;
      if (isSlowRunStatus(status)) return 30000;
      return 3000;
    },
  });
}

// Start a new simulation run
export function useStartSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: StartSimulationRequest) => startSimulationRequest(req),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['simulation-runs'] });
    },
  });
}

// Cancel an in-progress simulation run
export function useCancelRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => cancelRun(runId),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['simulation-runs'] });
    },
  });
}

// Resume a paused/budget-exhausted/failed simulation run
export function useResumeRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => resumeRunRequest(runId),
    onSettled: (_data, _error, runId) => {
      queryClient.invalidateQueries({ queryKey: ['simulation-runs'] });
      queryClient.invalidateQueries({ queryKey: ['simulation-run-status', runId] });
    },
  });
}

// Pause a running simulation run
export function usePauseRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => pauseRunRequest(runId),
    onSettled: (_data, _error, runId) => {
      queryClient.invalidateQueries({ queryKey: ['simulation-runs'] });
      queryClient.invalidateQueries({ queryKey: ['simulation-run-status', runId] });
    },
  });
}

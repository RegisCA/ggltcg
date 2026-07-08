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
} from '../api/simulationService';
import type {
  StartSimulationRequest,
  SimulationRunStatus,
} from '../api/simulationService';
import type { SimulationDeck, SimulationRun } from '../components/admin/types';

export const TERMINAL_RUN_STATUSES = ['completed', 'failed', 'cancelled'] as const;

export const isTerminalRunStatus = (status: string | undefined): boolean =>
  !!status && (TERMINAL_RUN_STATUSES as readonly string[]).includes(status);

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
    refetchInterval: (query) =>
      isTerminalRunStatus(query.state.data?.status) ? false : 3000,
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

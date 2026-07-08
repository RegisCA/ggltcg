/**
 * Simulation tab — configuration panel, active-run progress, results
 * matrix, and past runs. JSX moved verbatim from AdminDataViewer.tsx.
 *
 * The active-run progress poll now runs through useRunStatus (useQuery with
 * a refetchInterval that stops on terminal status) instead of the old
 * manual setInterval — same 3s cadence, same UI states.
 */

import React, { useEffect, useState } from 'react';
import {
  getRunResults,
  getGameDetail as getSimulationGameDetail,
} from '../../../api/simulationService';
import {
  useSimulationDecks,
  useSupportedModels,
  useSimulationRunsList,
  useRunStatus,
  useStartSimulation,
  useResumeRun,
  usePauseRun,
  isTerminalRunStatus,
} from '../../../hooks/useSimulationRuns';
import type {
  SimulationGameDetail,
  SimulationRun,
  MatchupStats,
  SimulationResults,
} from '../types';
import {
  formatDate,
  formatRelativeTime,
  formatCountdown,
  formatMaybeNumber,
  countSymptoms,
  totalCount,
  formatCountsInline,
  computeActiveTurnChargeAveragesFromSimulation,
} from '../utils';
import StatusBadge from '../shared/StatusBadge';

// Rough est. requests = total games x 6 turns x ~1.3 AI calls/turn, rounded
// up. This is a coarse planning number, not a guarantee — actual call
// counts vary with deck/strategy and card effects.
const CALLS_PER_TURN_ESTIMATE = 1.3;
const TURNS_PER_GAME_ESTIMATE = 6;

const estimateRequests = (totalGames: number): number =>
  Math.ceil(totalGames * TURNS_PER_GAME_ESTIMATE * CALLS_PER_TURN_ESTIMATE);

const SimulationTab: React.FC = () => {
  // Simulation state
  const [selectedDecks, setSelectedDecks] = useState<string[]>([]);
  // Model selects initialize from the fetched models list (first entry) so
  // an untouched form always submits exactly what the dropdowns display.
  const [player1Model, setPlayer1Model] = useState('');
  const [player2Model, setPlayer2Model] = useState('');
  const [iterationsPerMatchup, setIterationsPerMatchup] = useState(10);
  // Optional batch throttle controls — blank means unlimited/default.
  const [rpm, setRpm] = useState('');
  const [dailyRequestBudget, setDailyRequestBudget] = useState('');
  const [parallelGames, setParallelGames] = useState('10');
  const [isRunningSimulation, setIsRunningSimulation] = useState(false);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [runProgress, setRunProgress] = useState<{ completed: number; total: number; status: string } | null>(null);
  const [selectedSimulation, setSelectedSimulation] = useState<SimulationResults | null>(null);
  const [selectedGameDetail, setSelectedGameDetail] = useState<SimulationGameDetail | null>(null);
  const [loadingGameDetail, setLoadingGameDetail] = useState(false);
  // Per-run inline error (e.g. 409 "already resumed elsewhere") keyed by run_id
  const [runActionErrors, setRunActionErrors] = useState<Record<number, string>>({});

  // Fetch simulation decks / models / runs (tab is only mounted when active)
  const { data: simulationDecks } = useSimulationDecks(true);
  const { data: supportedModels } = useSupportedModels(true);
  const { data: simulationRuns, refetch: refetchSimulationRuns } = useSimulationRunsList(true);

  const startSimulationMutation = useStartSimulation();
  const resumeRunMutation = useResumeRun();
  const pauseRunMutation = usePauseRun();

  // Poll active run status (stops on its own once the status is terminal;
  // slows to 30s while paused/budget_exhausted)
  const { data: runStatus } = useRunStatus(activeRunId);

  // Default both model selects to the first fetched model once the list
  // loads (backend's default_simulation_model resolution puts it first).
  useEffect(() => {
    if (!supportedModels || supportedModels.length === 0) return;
    setPlayer1Model(prev => (prev === '' ? supportedModels[0] : prev));
    setPlayer2Model(prev => (prev === '' ? supportedModels[0] : prev));
  }, [supportedModels]);

  const clearRunActionError = (runId: number) => {
    setRunActionErrors(prev => {
      if (!(runId in prev)) return prev;
      const next = { ...prev };
      delete next[runId];
      return next;
    });
  };

  const extractErrorDetail = (error: unknown): string => {
    const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
    if (axiosError.response?.status === 409) {
      return axiosError.response?.data?.detail || 'Run already resumed/paused elsewhere';
    }
    return axiosError.response?.data?.detail || 'Unknown error';
  };

  const handleResumeRun = (runId: number) => {
    clearRunActionError(runId);
    resumeRunMutation.mutate(runId, {
      onError: (error) => {
        setRunActionErrors(prev => ({ ...prev, [runId]: extractErrorDetail(error) }));
      },
    });
  };

  const handlePauseRun = (runId: number) => {
    clearRunActionError(runId);
    pauseRunMutation.mutate(runId, {
      onError: (error) => {
        setRunActionErrors(prev => ({ ...prev, [runId]: extractErrorDetail(error) }));
      },
    });
  };

  useEffect(() => {
    if (!activeRunId || !runStatus) return;

    setRunProgress({
      completed: runStatus.completed_games,
      total: runStatus.total_games,
      status: runStatus.status,
    });

    // Check if simulation is done
    if (isTerminalRunStatus(runStatus.status)) {
      setIsRunningSimulation(false);
      setActiveRunId(null);

      if (runStatus.status === 'completed') {
        // Load full results
        getRunResults(activeRunId)
          .then(results => setSelectedSimulation(results))
          .catch(error => {
            console.error('Failed to load simulation results:', error);
            alert('Failed to load simulation results');
          });
      } else {
        alert(`Simulation ${runStatus.status}: ${runStatus.error_message || 'Unknown error'}`);
      }

      refetchSimulationRuns();
    }
  }, [activeRunId, runStatus, refetchSimulationRuns]);

  // Simulation functions
  const toggleDeckSelection = (deckName: string) => {
    setSelectedDecks(prev =>
      prev.includes(deckName)
        ? prev.filter(d => d !== deckName)
        : [...prev, deckName]
    );
  };

  const startSimulation = async () => {
    if (selectedDecks.length < 1) {
      alert('Please select at least 1 deck');
      return;
    }
    if (!player1Model || !player2Model) {
      alert('Models are still loading — try again in a moment');
      return;
    }

    setIsRunningSimulation(true);
    setRunProgress(null);

    try {
      // Start simulation (returns immediately with run_id)
      const parsedRpm = rpm.trim() === '' ? null : parseInt(rpm, 10);
      const parsedDailyBudget = dailyRequestBudget.trim() === '' ? null : parseInt(dailyRequestBudget, 10);
      const parsedParallelGames = parallelGames.trim() === '' ? 10 : parseInt(parallelGames, 10);

      const startResponse = await startSimulationMutation.mutateAsync({
        deck_names: selectedDecks,
        player1_model: player1Model,
        player2_model: player2Model,
        iterations_per_matchup: iterationsPerMatchup,
        max_turns: 20,
        rpm: parsedRpm,
        daily_request_budget: parsedDailyBudget,
        parallel_games: parsedParallelGames,
      });

      const runId = startResponse.run_id;
      setActiveRunId(runId);
      setRunProgress({
        completed: 0,
        total: startResponse.total_games,
        status: 'pending',
      });
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      console.error('Failed to start simulation:', error);
      alert(`Failed to start simulation: ${axiosError.response?.data?.detail || 'Unknown error'}`);
      setIsRunningSimulation(false);
      setActiveRunId(null);
      setRunProgress(null);
    }
  };

  const loadSimulationResults = async (runId: number) => {
    try {
      const results = await getRunResults(runId);
      setSelectedSimulation(results);
      setSelectedGameDetail(null); // Clear any game detail when switching runs
    } catch (error) {
      console.error('Failed to load simulation results:', error);
      alert('Failed to load simulation results');
    }
  };

  const loadGameDetail = async (runId: number, gameNumber: number) => {
    setLoadingGameDetail(true);
    try {
      const detail = await getSimulationGameDetail(runId, gameNumber);
      setSelectedGameDetail(detail);
    } catch (error) {
      console.error('Failed to load game detail:', error);
      alert('Failed to load game detail');
    } finally {
      setLoadingGameDetail(false);
    }
  };

  return (
    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-lg)' }}>
      {/* Configuration Panel */}
      {!selectedSimulation && (
        <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
          <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}>
            New Simulation
          </h2>

          {/* Deck Selection */}
          <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
            <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
              Select Decks
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 'var(--spacing-component-sm)' }}>
              {simulationDecks?.map(deck => (
                <div
                  key={deck.name}
                  className={`cursor-pointer rounded-lg border-2 transition-colors ${
                    selectedDecks.includes(deck.name)
                      ? 'border-blue-500 bg-blue-900/30'
                      : 'border-white/15 bg-black/20 hover:border-white/20'
                  }`}
                  style={{ padding: 'var(--spacing-component-md)' }}
                  onClick={() => toggleDeckSelection(deck.name)}
                >
                  <div className="font-semibold">{deck.name}</div>
                  <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                    {deck.description}
                  </div>
                  <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: '4px' }}>
                    {deck.cards.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Selection */}
          <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-lg)' }}>
            <div>
              <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                Player 1 Model
              </label>
              <select
                value={player1Model}
                onChange={e => setPlayer1Model(e.target.value)}
                className="w-full bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
                style={{ padding: 'var(--spacing-component-sm)' }}
              >
                {supportedModels?.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                Player 2 Model
              </label>
              <select
                value={player2Model}
                onChange={e => setPlayer2Model(e.target.value)}
                className="w-full bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
                style={{ padding: 'var(--spacing-component-sm)' }}
              >
                {supportedModels?.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Iterations */}
          <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
            <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
              Games per Matchup: {iterationsPerMatchup}
            </label>
            <input
              type="range"
              min="1"
              max="50"
              value={iterationsPerMatchup}
              onChange={e => setIterationsPerMatchup(parseInt(e.target.value))}
              className="w-full"
            />
            {(() => {
              const numDecks = selectedDecks.length;
              const numMatchups = numDecks * numDecks; // n² matchups (all directions + mirrors)
              const totalGames = numMatchups * iterationsPerMatchup;
              const MAX_GAMES = 500;
              const exceedsLimit = totalGames > MAX_GAMES;

              return (
                <div className="text-sm" style={{ marginTop: '4px' }}>
                  {numDecks >= 1 && (
                    <>
                      <span className="text-[var(--ink-faint)]">
                        {numMatchups} matchups ({numDecks}² = mirrors + both directions) × {iterationsPerMatchup} games ={' '}
                      </span>
                      <span className={`font-semibold ${exceedsLimit ? 'text-red-400' : 'text-[var(--ink-text)]'}`}>
                        {totalGames} total games
                      </span>
                      {exceedsLimit && (
                        <div className="text-red-400 mt-1">
                          ⚠️ Exceeds {MAX_GAMES} game limit. Reduce decks or games per matchup.
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })()}
          </div>

          {/* Batch Throttle Controls */}
          <div className="grid grid-cols-3" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-lg)' }}>
            <div>
              <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                RPM (optional)
              </label>
              <input
                type="number"
                min="1"
                placeholder="unlimited"
                value={rpm}
                onChange={e => setRpm(e.target.value)}
                className="w-full bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
                style={{ padding: 'var(--spacing-component-sm)' }}
              />
            </div>
            <div>
              <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                Daily request budget (optional)
              </label>
              <input
                type="number"
                min="1"
                placeholder="unlimited"
                value={dailyRequestBudget}
                onChange={e => setDailyRequestBudget(e.target.value)}
                className="w-full bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
                style={{ padding: 'var(--spacing-component-sm)' }}
              />
            </div>
            <div>
              <label className="block font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                Parallel games
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={parallelGames}
                onChange={e => setParallelGames(e.target.value)}
                className="w-full bg-black/20 border border-white/15 rounded text-[var(--ink-text)]"
                style={{ padding: 'var(--spacing-component-sm)' }}
              />
            </div>
          </div>

          {/* Rough request/duration estimate */}
          {(() => {
            const numDecks = selectedDecks.length;
            if (numDecks < 1) return null;
            const totalGames = numDecks * numDecks * iterationsPerMatchup;
            const estRequests = estimateRequests(totalGames);
            const parsedDailyBudget = dailyRequestBudget.trim() === '' ? null : parseInt(dailyRequestBudget, 10);
            const estDays = parsedDailyBudget && parsedDailyBudget > 0
              ? Math.ceil(estRequests / parsedDailyBudget)
              : null;

            return (
              <div className="text-xs text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                Rough estimate: ~{estRequests} AI requests ({totalGames} games × {TURNS_PER_GAME_ESTIMATE} turns × ~{CALLS_PER_TURN_ESTIMATE} calls/turn)
                {estDays !== null && <> · ~{estDays} {estDays === 1 ? 'day' : 'days'} at the configured daily budget</>}
                . Actual usage varies with deck/strategy.
              </div>
            );
          })()}

          {/* Start Button */}
          {(() => {
            const totalGames = selectedDecks.length * selectedDecks.length * iterationsPerMatchup;
            const MAX_GAMES = 500;
            const exceedsLimit = totalGames > MAX_GAMES;
            const modelsReady = player1Model !== '' && player2Model !== '';
            const isDisabled = isRunningSimulation || selectedDecks.length < 1 || exceedsLimit || !modelsReady;

            return (
              <button
                onClick={startSimulation}
                disabled={isDisabled}
                className={`w-full rounded font-semibold ${
                  isDisabled
                    ? 'bg-white/10 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                }`}
                style={{ padding: 'var(--spacing-component-md)' }}
              >
                {isRunningSimulation ? 'Starting...' : exceedsLimit ? 'Too Many Games' : 'Start Simulation'}
              </button>
            );
          })()}

          {/* Progress Display */}
          {isRunningSimulation && runProgress && (
            <div className="bg-blue-900/30 border border-blue-500 rounded" style={{ marginTop: 'var(--spacing-component-md)', padding: 'var(--spacing-component-md)' }}>
              <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                <span className="font-semibold">
                  Simulation {runProgress.status === 'pending' ? 'starting' : runProgress.status === 'running' ? 'in progress' : runProgress.status.replace('_', ' ')}...
                  <StatusBadge status={runProgress.status} className="ml-2" />
                </span>
                <span className="text-blue-400">
                  {runProgress.completed} / {runProgress.total} games
                </span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-3">
                <div
                  className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${runProgress.total > 0 ? (runProgress.completed / runProgress.total * 100) : 0}%` }}
                />
              </div>
              <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                {runProgress.total > 0 ? Math.round(runProgress.completed / runProgress.total * 100) : 0}% complete
                {activeRunId && <span> (Run #{activeRunId})</span>}
              </div>

              {activeRunId && runStatus?.budget && runProgress.status === 'budget_exhausted' && (
                <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                  Budget used: {runStatus.budget.used_today ?? '—'}/{runStatus.budget.daily_budget ?? '—'}
                  {formatCountdown(runStatus.budget.resets_at) && <span> · {formatCountdown(runStatus.budget.resets_at)}</span>}
                </div>
              )}

              {activeRunId && runProgress.status === 'running' && (
                <button
                  onClick={() => handlePauseRun(activeRunId)}
                  disabled={pauseRunMutation.isPending}
                  className="text-xs rounded bg-white/10 hover:bg-white/20 disabled:opacity-50"
                  style={{ marginTop: 'var(--spacing-component-sm)', padding: '2px var(--spacing-component-sm)' }}
                >
                  {pauseRunMutation.isPending ? 'Pausing...' : 'Pause'}
                </button>
              )}
              {activeRunId && (runProgress.status === 'budget_exhausted' || runProgress.status === 'paused') && (
                <button
                  onClick={() => handleResumeRun(activeRunId)}
                  disabled={resumeRunMutation.isPending}
                  className="text-xs rounded bg-green-600 hover:bg-green-700 disabled:opacity-50"
                  style={{ marginTop: 'var(--spacing-component-sm)', padding: '2px var(--spacing-component-sm)' }}
                >
                  {resumeRunMutation.isPending ? 'Resuming...' : 'Resume'}
                </button>
              )}
              {activeRunId && runActionErrors[activeRunId] && (
                <div className="text-xs text-red-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                  {runActionErrors[activeRunId]}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Results Panel */}
      {selectedSimulation && (
        <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
          <button
            onClick={() => setSelectedSimulation(null)}
            className="bg-blue-600 hover:bg-blue-700 text-[var(--ink-text)] rounded"
            style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)', alignSelf: 'flex-start' }}
          >
            ← Back to Configuration
          </button>

          <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}>
              Simulation Results
              <StatusBadge status={selectedSimulation.status} className="ml-2" />
            </h2>

            {/* Config Summary */}
            <div className="text-sm text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
              <div>Decks: {selectedSimulation.config.deck_names.join(', ')}</div>
              <div className="bg-black/20/50 rounded p-2 mt-2">
                <div className="font-semibold text-[var(--ink-text)] mb-1">Model Assignment:</div>
                <div className="flex gap-4">
                  <span><span className="text-green-400">Player 1 / Deck 1:</span> {selectedSimulation.config.player1_model}</span>
                  <span><span className="text-blue-400">Player 2 / Deck 2:</span> {selectedSimulation.config.player2_model}</span>
                </div>
                <div className="text-xs text-[var(--ink-faint)] mt-1">Note: Player 1 always goes first (receives 2 Charge on turn 1 instead of 4)</div>
              </div>
              <div style={{ marginTop: '8px' }}>Games: {selectedSimulation.completed_games}/{selectedSimulation.total_games}</div>
              {selectedSimulation.aggregate && (
                <div className="bg-black/20/50 rounded p-2 mt-2">
                  <div className="text-xs text-[var(--ink-muted)]">
                    <span className="text-[var(--ink-faint)]">Avg Charge end (active turns): </span>
                    <span className="text-green-400">P1</span>
                    <span className="text-[var(--ink-muted)]"> {formatMaybeNumber(selectedSimulation.aggregate.avg_p1_charge_end_active, 2)} </span>
                    <span className="text-[var(--ink-faint)]">·</span>
                    <span className="text-blue-400"> P2</span>
                    <span className="text-[var(--ink-muted)]"> {formatMaybeNumber(selectedSimulation.aggregate.avg_p2_charge_end_active, 2)}</span>
                  </div>
                  <div className="text-xs text-[var(--ink-muted)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                    <span className="text-[var(--ink-faint)]">Avg turns: </span>
                    <span className="text-orange-400">{formatMaybeNumber(selectedSimulation.aggregate.avg_turns, 1)}</span>
                    <span className="text-[var(--ink-faint)]"> · </span>
                    <span className="text-[var(--ink-faint)]">Turn-limit hits (T{selectedSimulation.aggregate.max_turns}): </span>
                    <span className="text-[var(--ink-muted)]">{selectedSimulation.aggregate.turn_limit_hits}/{selectedSimulation.completed_games}</span>
                    <span className="text-[var(--ink-faint)]"> ({selectedSimulation.aggregate.turn_limit_hit_pct}%)</span>
                  </div>
                </div>
              )}
              {selectedSimulation.completed_at && (
                <div>Completed: {formatDate(selectedSimulation.completed_at)}</div>
              )}
            </div>

            {/* Matchup Results Matrix */}
            <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-sm)' }}>
              Matchup Results Matrix
              <span className="text-sm font-normal text-[var(--ink-faint)] ml-2">(Row Deck as P1 vs Column Deck as P2)</span>
            </h3>
            {(() => {
              // Build matrix data from matchup_stats
              const deckNames = [...new Set(
                Object.values(selectedSimulation.matchup_stats).flatMap(s => [s.deck1_name, s.deck2_name])
              )].sort();

              // Create lookup map for matchups
              const matchupMap = new Map<string, MatchupStats>();
              Object.values(selectedSimulation.matchup_stats).forEach(stats => {
                matchupMap.set(`${stats.deck1_name}_vs_${stats.deck2_name}`, stats);
              });

              // Helper to get cell color based on win rate
              const getWinRateColor = (winRate: number) => {
                if (winRate >= 0.7) return 'bg-green-600';
                if (winRate >= 0.55) return 'bg-green-800';
                if (winRate > 0.45) return 'bg-white/10';
                if (winRate > 0.3) return 'bg-red-900';
                return 'bg-red-700';
              };

              return (
                <div className="bg-black/20 rounded overflow-hidden" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                  <table className="w-full text-sm">
                    <thead className="bg-black/30">
                      <tr>
                        <th className="px-3 py-2 text-left border-r border-white/10">
                          <span className="text-green-400">P1 (Row)</span>
                          <span className="text-[var(--ink-faint)]"> \ </span>
                          <span className="text-blue-400">P2 (Col)</span>
                        </th>
                        {deckNames.map(deck => (
                          <th key={deck} className="px-3 py-2 text-center text-blue-400 font-medium" style={{ minWidth: '90px' }}>
                            {deck}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {deckNames.map(rowDeck => (
                        <tr key={rowDeck} className="border-t border-white/10">
                          <td className="px-3 py-2 font-medium text-green-400 border-r border-white/10">{rowDeck}</td>
                          {deckNames.map(colDeck => {
                            const stats = matchupMap.get(`${rowDeck}_vs_${colDeck}`);
                            const isMirror = rowDeck === colDeck;

                            if (!stats) {
                              return (
                                <td key={colDeck} className={`px-3 py-2 text-center ${isMirror ? 'bg-panel' : ''} text-[var(--ink-faint)]`}>
                                  {isMirror ? '—' : 'N/A'}
                                </td>
                              );
                            }
                            return (
                              <td
                                key={colDeck}
                                className={`px-3 py-2 text-center ${getWinRateColor(stats.deck1_win_rate)} ${isMirror ? 'ring-1 ring-gray-500' : ''}`}
                                title={`${stats.deck1_wins}W / ${stats.deck2_wins}L / ${stats.draws}D (${stats.games_played} games, avg ${stats.avg_turns.toFixed(1)} turns)`}
                              >
                                <div className="font-bold">{(stats.deck1_win_rate * 100).toFixed(0)}%</div>
                                <div className="text-xs opacity-75">{stats.deck1_wins}-{stats.deck2_wins}</div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 text-xs text-[var(--ink-faint)] border-t border-white/10">
                    <span className="inline-block w-4 h-3 bg-green-600 mr-1"></span>≥70%
                    <span className="inline-block w-4 h-3 bg-green-800 mx-1 ml-3"></span>55-69%
                    <span className="inline-block w-4 h-3 bg-white/10 mx-1 ml-3"></span>45-55%
                    <span className="inline-block w-4 h-3 bg-red-900 mx-1 ml-3"></span>31-44%
                    <span className="inline-block w-4 h-3 bg-red-700 mx-1 ml-3"></span>≤30%
                  </div>
                </div>
              );
            })()}

            {/* Individual Games */}
            <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-sm)' }}>
              Individual Games
              <span className="text-sm font-normal text-[var(--ink-faint)] ml-2">(click to view details)</span>
            </h3>
            <div className="bg-black/20 rounded overflow-hidden max-h-[600px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-black/30 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-2 text-left">#</th>
                    <th className="px-4 py-2 text-left">Matchup</th>
                    <th className="px-4 py-2 text-center">Result</th>
                    <th className="px-4 py-2 text-center text-green-400" title="Player 1 Total Charge Spent">P1 Charge</th>
                    <th className="px-4 py-2 text-center text-blue-400" title="Player 2 Total Charge Spent">P2 Charge</th>
                    <th className="px-4 py-2 text-center" title="Per-game avg Charge at end of active turns">Avg Charge end</th>
                    <th className="px-4 py-2 text-center">Turns</th>
                    <th className="px-4 py-2 text-center">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedSimulation.games.map(game => (
                    <React.Fragment key={game.game_number}>
                      <tr
                        className={`border-t border-white/10 cursor-pointer hover:bg-panel ${selectedGameDetail?.game_number === game.game_number ? 'bg-white/10' : ''}`}
                        onClick={() => {
                          if (selectedGameDetail?.game_number === game.game_number) {
                            setSelectedGameDetail(null);
                          } else {
                            loadGameDetail(selectedSimulation.run_id, game.game_number);
                          }
                        }}
                      >
                        <td className="px-4 py-2">
                          {game.game_number}
                          <span className="ml-2 text-[var(--ink-faint)]">{selectedGameDetail?.game_number === game.game_number ? '▼' : '▶'}</span>
                        </td>
                        <td className="px-4 py-2">
                          <span className="text-green-400">{game.deck1_name}</span>
                          <span className="text-[var(--ink-faint)]"> vs </span>
                          <span className="text-blue-400">{game.deck2_name}</span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          {game.outcome === 'draw' ? (
                            <span className="text-[var(--ink-faint)]">Draw</span>
                          ) : (
                            <span className={game.outcome === 'player1_win' ? 'text-green-400' : 'text-blue-400'}>
                              {game.winner_deck} wins
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-center text-green-400">{game.p1_charge_spent}</td>
                        <td className="px-4 py-2 text-center text-blue-400">{game.p2_charge_spent}</td>
                        <td className="px-4 py-2 text-center text-[var(--ink-muted)]">
                          <span className="text-green-400">P1</span>
                          <span className="text-[var(--ink-muted)]"> {formatMaybeNumber(game.p1_avg_charge_end_active, 2)}</span>
                          <span className="text-[var(--ink-faint)]"> · </span>
                          <span className="text-blue-400">P2</span>
                          <span className="text-[var(--ink-muted)]"> {formatMaybeNumber(game.p2_avg_charge_end_active, 2)}</span>
                        </td>
                        <td className="px-4 py-2 text-center text-orange-400">
                          {game.turn_count}
                          {game.hit_turn_limit && (
                            <span className="ml-2 text-xs rounded bg-red-700/60 text-red-100" style={{ padding: '2px 6px' }} title="Hit simulation turn limit">
                              TL
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-center text-cyan-400">
                          {(game.duration_ms / 1000).toFixed(1)}s
                        </td>
                      </tr>
                      {/* Inline detail panel */}
                      {selectedGameDetail?.game_number === game.game_number && (
                        <tr>
                          <td colSpan={8} className="p-0">
                            <div className="bg-panel border-l-4 border-blue-500 p-4">
                              {loadingGameDetail ? (
                                <div className="text-center text-[var(--ink-faint)] py-4">Loading game details...</div>
                              ) : selectedGameDetail.charge_tracking && selectedGameDetail.charge_tracking.length > 0 ? (
                                <div>
                                  <div className="flex justify-between items-center mb-3">
                                    <h4 className="font-semibold">Game #{selectedGameDetail.game_number} Details</h4>
                                  </div>

                                  {/* Debug Metrics */}
                                  {(() => {
                                    const chargeAverages = computeActiveTurnChargeAveragesFromSimulation(selectedGameDetail.charge_tracking);
                                    const blobParts: string[] = [];
                                    for (const a of selectedGameDetail.action_log || []) {
                                      if (a.description) blobParts.push(a.description);
                                      if (a.reasoning) blobParts.push(a.reasoning);
                                    }
                                    if (selectedGameDetail.error_message) blobParts.push(selectedGameDetail.error_message);
                                    const symptomCounts = countSymptoms(blobParts.join('\n'));
                                    return (
                                      <div className="bg-black/20 rounded" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                                        <div className="text-sm text-[var(--ink-muted)]">
                                          <span className="text-[var(--ink-faint)]">Avg Charge end (active turns): </span>
                                          <span className="text-green-400">P1</span>
                                          <span className="text-[var(--ink-muted)]"> {chargeAverages.p1_avg !== null ? chargeAverages.p1_avg.toFixed(2) : '—'} </span>
                                          <span className="text-[var(--ink-faint)]">({chargeAverages.p1_samples} turns)</span>
                                          <span className="text-[var(--ink-faint)]"> · </span>
                                          <span className="text-blue-400">P2</span>
                                          <span className="text-[var(--ink-muted)]"> {chargeAverages.p2_avg !== null ? chargeAverages.p2_avg.toFixed(2) : '—'} </span>
                                          <span className="text-[var(--ink-faint)]">({chargeAverages.p2_samples} turns)</span>
                                        </div>
                                        <div className="text-sm text-[var(--ink-muted)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                                          <span className="text-[var(--ink-faint)]">Symptoms (game): </span>
                                          <span>{formatCountsInline(symptomCounts)}</span>
                                          <span className="text-[var(--ink-faint)]"> · total {totalCount(symptomCounts)}</span>
                                        </div>
                                      </div>
                                    );
                                  })()}

                                  {/* Charge Tracking - Compact timeline view */}
                                  <div className="overflow-x-auto mb-4">
                                    <table className="w-full text-sm border-collapse">
                                      <thead className="bg-black/20">
                                        <tr>
                                          <th className="px-3 py-2 text-center border-b border-white/10 w-16">Turn</th>
                                          <th className="px-3 py-2 text-center text-green-400 border-b border-white/10 w-32">P1 Charge</th>
                                          <th className="px-3 py-2 text-center text-blue-400 border-b border-white/10 w-32">P2 Charge</th>
                                          <th className="px-3 py-2 text-left border-b border-white/10">Actions</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {(() => {
                                          // Group Charge tracking by turn
                                          const turnMap = new Map<number, { p1?: typeof selectedGameDetail.charge_tracking[0], p2?: typeof selectedGameDetail.charge_tracking[0] }>();
                                          selectedGameDetail.charge_tracking.forEach(charge => {
                                            if (!turnMap.has(charge.turn)) turnMap.set(charge.turn, {});
                                            const entry = turnMap.get(charge.turn)!;
                                            if (charge.player_id === 'player1') entry.p1 = charge;
                                            else entry.p2 = charge;
                                          });
                                          // Include turns from action_log even if not in charge_tracking (e.g., final turn)
                                          const allTurns = new Set<number>(turnMap.keys());
                                          selectedGameDetail.action_log?.forEach(action => allTurns.add(action.turn));
                                          const turns = Array.from(allTurns).sort((a, b) => a - b);

                                          // Group actions by turn
                                          const actionsByTurn = new Map<number, typeof selectedGameDetail.action_log>();
                                          selectedGameDetail.action_log?.forEach(action => {
                                            if (!actionsByTurn.has(action.turn)) actionsByTurn.set(action.turn, []);
                                            actionsByTurn.get(action.turn)!.push(action);
                                          });

                                          // Format Charge change as compact string with proper spacing
                                          const formatCharge = (data: typeof selectedGameDetail.charge_tracking[0] | undefined, isActive: boolean): React.ReactNode => {
                                            if (!data) return <span className="text-[var(--ink-faint)]">—</span>;
                                            return (
                                              <span className={`font-mono ${isActive ? '' : 'opacity-60'}`}>
                                                <span>{data.charge_start}</span>
                                                {data.charge_gained > 0 && <span className="text-yellow-400 ml-1">+{data.charge_gained}</span>}
                                                {data.charge_spent > 0 && <span className="text-red-400 ml-1">-{data.charge_spent}</span>}
                                                <span className="text-[var(--ink-faint)] mx-1">→</span>
                                                <span className="font-bold">{data.charge_end}</span>
                                              </span>
                                            );
                                          };

                                          return turns.map(turn => {
                                            const data = turnMap.get(turn)!;
                                            const turnActions = actionsByTurn.get(turn) || [];
                                            const isP1Turn = turn % 2 === 1; // Odd turns = P1, even turns = P2

                                            const visibleActions = turnActions.filter(a => a.action !== 'end_turn');

                                            return (
                                              <tr key={turn} className="border-t border-white/10 hover:bg-white/5">
                                                <td className="px-3 py-2 text-center font-bold">{turn}</td>
                                                <td className={`px-3 py-2 text-center ${isP1Turn ? 'bg-green-900/20' : ''}`}>
                                                  {formatCharge(data.p1, isP1Turn)}
                                                </td>
                                                <td className={`px-3 py-2 text-center ${!isP1Turn ? 'bg-blue-900/20' : ''}`}>
                                                  {formatCharge(data.p2, !isP1Turn)}
                                                </td>
                                                <td className="px-3 py-2 text-left text-xs">
                                                  {visibleActions.slice(0, 10).map((a, i) => (
                                                    <React.Fragment key={i}>
                                                      {i > 0 && <span className="text-[var(--ink-faint)]">, </span>}
                                                      <span className={a.player === 'player1' ? 'text-green-400' : 'text-blue-400'}>
                                                        {a.description || `${a.action} ${a.card || ''}`}
                                                      </span>
                                                    </React.Fragment>
                                                  ))}
                                                  {visibleActions.length > 10 && <span className="text-[var(--ink-faint)]"> +{visibleActions.length - 10} more</span>}
                                                </td>
                                              </tr>
                                            );
                                          });
                                        })()}
                                        {/* Summary row aligned with columns */}
                                        <tr className="border-t border-white/10 bg-black/20/50">
                                          <td className="px-3 py-2 text-center text-xs text-[var(--ink-faint)]">Total</td>
                                          <td className="px-3 py-2 text-center text-green-400 text-xs">
                                            <span className="text-yellow-400">+{selectedGameDetail.charge_tracking.filter(charge => charge.player_id === 'player1').reduce((sum, charge) => sum + charge.charge_gained, 0)}</span>
                                            <span className="text-red-400 ml-1">-{selectedGameDetail.charge_tracking.filter(charge => charge.player_id === 'player1').reduce((sum, charge) => sum + charge.charge_spent, 0)}</span>
                                          </td>
                                          <td className="px-3 py-2 text-center text-blue-400 text-xs">
                                            <span className="text-yellow-400">+{selectedGameDetail.charge_tracking.filter(charge => charge.player_id === 'player2').reduce((sum, charge) => sum + charge.charge_gained, 0)}</span>
                                            <span className="text-red-400 ml-1">-{selectedGameDetail.charge_tracking.filter(charge => charge.player_id === 'player2').reduce((sum, charge) => sum + charge.charge_spent, 0)}</span>
                                          </td>
                                          <td></td>
                                        </tr>
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              ) : (
                                <div className="text-[var(--ink-faint)]">No Charge tracking data available.</div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Past Simulations */}
      {!selectedSimulation && simulationRuns && simulationRuns.length > 0 && (
        <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
          <h2 className="text-xl font-bold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}>
            Past Simulations
          </h2>
          <div className="text-xs text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-md)' }}>
            Runs started from the CLI appear here too, when the backend points at the same database.
          </div>
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
            {simulationRuns.map((run: SimulationRun) => {
              const isNonTerminalNonCompleted = run.status !== 'completed';
              const progressPct = run.total_games > 0 ? (run.completed_games / run.total_games) * 100 : 0;

              return (
                <div
                  key={run.run_id}
                  className="bg-black/20 rounded-lg"
                  style={{ padding: 'var(--spacing-component-md)' }}
                >
                  <div
                    className="flex justify-between items-center cursor-pointer hover:bg-white/5 -m-1 p-1 rounded"
                    onClick={() => loadSimulationResults(run.run_id)}
                  >
                    <div className="flex-1">
                      <div className="font-semibold">
                        Run #{run.run_id}
                        <StatusBadge status={run.status} className="ml-2" />
                      </div>
                      <div className="text-sm text-[var(--ink-faint)]">
                        {run.config.deck_names.join(', ')} • {run.completed_games}/{run.total_games} games
                      </div>
                      <div className="text-xs text-[var(--ink-faint)]">
                        {formatRelativeTime(run.created_at)}
                      </div>
                      {isNonTerminalNonCompleted && (
                        <div className="w-full bg-white/10 rounded-full h-2" style={{ marginTop: 'var(--spacing-component-xs)', maxWidth: '240px' }}>
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progressPct}%` }}
                          />
                        </div>
                      )}
                      {run.status === 'budget_exhausted' && run.budget && (
                        <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                          Budget used: {run.budget.used_today ?? '—'}/{run.budget.daily_budget ?? '—'}
                          {formatCountdown(run.budget.resets_at) && <span> · {formatCountdown(run.budget.resets_at)}</span>}
                        </div>
                      )}
                    </div>
                    <div className="text-blue-400">View →</div>
                  </div>

                  <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)' }}>
                    {run.status === 'running' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handlePauseRun(run.run_id); }}
                        disabled={pauseRunMutation.isPending}
                        className="text-xs rounded bg-white/10 hover:bg-white/20 disabled:opacity-50"
                        style={{ padding: '2px var(--spacing-component-sm)' }}
                      >
                        {pauseRunMutation.isPending ? 'Pausing...' : 'Pause'}
                      </button>
                    )}
                    {(run.status === 'paused' || run.status === 'budget_exhausted') && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleResumeRun(run.run_id); }}
                        disabled={resumeRunMutation.isPending}
                        className="text-xs rounded bg-green-600 hover:bg-green-700 disabled:opacity-50"
                        style={{ padding: '2px var(--spacing-component-sm)' }}
                      >
                        {resumeRunMutation.isPending ? 'Resuming...' : 'Resume'}
                      </button>
                    )}
                    {runActionErrors[run.run_id] && (
                      <span className="text-xs text-red-400">{runActionErrors[run.run_id]}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default SimulationTab;

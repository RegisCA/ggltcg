/**
 * Admin data viewer for GGLTCG database.
 * 
 * Simple interface to view AI logs, game playbacks, and stats.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface SummaryStats {
  users: { total: number };
  games: {
    total: number;
    active: number;
    completed: number;
    recent_24h: number;
  };
  ai_logs: {
    total: number;
    recent_1h: number;
  };
  playbacks: {
    total: number;
  };
}

interface AILog {
  id: number;
  game_id: string;
  turn_number: number;
  player_id: string;
  model_name: string;
  prompts_version: string;
  prompt: string;
  response: string;
  action_number: number | null;
  reasoning: string | null;
  created_at: string;
  // V3 fields
  ai_version: number | null;
  turn_plan: {
    strategy: string;
    total_actions: number;
    current_action: number;
    cc_start: number;
    cc_after_plan: number;
    expected_cards_slept: number;
    cc_efficiency: string;
    // Full action sequence (new)
    action_sequence?: Array<{
      action_type: string;
      card_name: string | null;
      target_names: string[] | null;
      cc_cost: number;
      reasoning: string;
    }>;
    // Planning prompt/response (new)
    planning_prompt?: string;
    planning_response?: string;
    // Execution tracking (new)
    execution_log?: Array<{
      action_index: number;
      planned_action: string;
      status: 'success' | 'failed' | 'fallback_to_llm' | 'execution_failed';
      method?: 'heuristic' | 'llm';
      reason?: string;
      execution_confirmed?: boolean;
    }>;
  } | null;
  plan_execution_status: 'complete' | 'fallback' | null;
  fallback_reason: string | null;
  planned_action_index: number | null;
}

interface GamePlayback {
  id: number;
  game_id: string;
  player1_id: string;
  player1_name: string;
  player2_id: string;
  player2_name: string;
  winner_id: string | null;
  turn_count: number;
  created_at: string;
  completed_at: string | null;
}

interface GamePlaybackDetail extends GamePlayback {
  first_player_id: string;
  starting_deck_p1: string[];
  starting_deck_p2: string[];
  play_by_play: Array<{
    turn: number;
    player: string;
    action_type: string;
    description: string;
  }>;
  cc_tracking: TurnCC[] | null;
}

interface Game {
  id: string;
  status: string;
  player1_id: string;
  player1_name: string;
  player2_id: string;
  player2_name: string;
  game_code: string | null;
  turn_number: number;
  phase: string;
  winner_id: string | null;
  created_at: string;
  updated_at: string;
}

interface User {
  google_id: string;
  first_name: string;
  display_name: string;
  created_at: string;
  updated_at: string;
  games_played: number;
  games_won: number;
  win_rate: number;
  avg_turns: number;
  avg_game_duration_seconds: number;
  last_game_at: string | null;
  last_game_status: string | null;
  favorite_decks: string[][];
}

// CC Tracking interface
interface TurnCC {
  turn: number;
  player_id: string;
  cc_start: number;
  cc_gained: number;
  cc_spent: number;
  cc_end: number;
}

// Action log interface
interface ActionLogEntry {
  turn: number;
  player: string;
  action: string;
  card: string | null;
  description: string;
  reasoning: string;
}

interface SimulationGameDetail {
  game_number: number;
  deck1_name: string;
  deck2_name: string;
  outcome: string;
  winner_deck: string | null;
  turn_count: number;
  duration_ms: number;
  error_message: string | null;
  cc_tracking: TurnCC[];
  action_log: ActionLogEntry[];
  player1_model: string;
  player2_model: string;
}

// Simulation interfaces
interface SimulationDeck {
  name: string;
  description: string;
  cards: string[];
}

interface SimulationRun {
  run_id: number;
  status: string;
  total_games: number;
  completed_games: number;
  config: {
    deck_names: string[];
    player1_model: string;
    player2_model: string;
    iterations_per_matchup: number;
    max_turns: number;
  };
  created_at: string;
  completed_at: string | null;
}

interface MatchupStats {
  deck1_name: string;
  deck2_name: string;
  games_played: number;
  deck1_wins: number;
  deck2_wins: number;
  draws: number;
  deck1_win_rate: number;
  deck2_win_rate: number;
  avg_turns: number;
  avg_duration_ms: number;
}

interface SimulationResults {
  run_id: number;
  status: string;
  config: SimulationRun['config'];
  total_games: number;
  completed_games: number;
  matchup_stats: Record<string, MatchupStats>;
  games: Array<{
    game_number: number;
    deck1_name: string;
    deck2_name: string;
    outcome: string;
    winner_deck: string | null;
    turn_count: number;
    duration_ms: number;
    p1_cc_spent: number;
    p2_cc_spent: number;
    error_message: string | null;
  }>;
  created_at: string;
  completed_at: string | null;
}

const AdminDataViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'summary' | 'ai-logs' | 'games' | 'playbacks' | 'users' | 'simulation'>('summary');
  const [selectedLog, setSelectedLog] = useState<AILog | null>(null);
  const [expandedTurns, setExpandedTurns] = useState<Set<string>>(new Set());
  const [selectedPlayback, setSelectedPlayback] = useState<GamePlaybackDetail | null>(null);
  const [aiLogsGameIdFilter, setAiLogsGameIdFilter] = useState<string | null>(null);
  
  // Simulation state
  const [selectedDecks, setSelectedDecks] = useState<string[]>([]);
  const [player1Model, setPlayer1Model] = useState('gemini-2.5-flash-lite');
  const [player2Model, setPlayer2Model] = useState('gemini-2.0-flash');
  const [iterationsPerMatchup, setIterationsPerMatchup] = useState(10);
  const [isRunningSimulation, setIsRunningSimulation] = useState(false);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [runProgress, setRunProgress] = useState<{ completed: number; total: number; status: string } | null>(null);
  const [selectedSimulation, setSelectedSimulation] = useState<SimulationResults | null>(null);
  const [selectedGameDetail, setSelectedGameDetail] = useState<SimulationGameDetail | null>(null);
  const [loadingGameDetail, setLoadingGameDetail] = useState(false);
  
  // Ref for polling interval cleanup
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollErrorCountRef = useRef<number>(0);
  const MAX_POLL_ERRORS = 10;
  
  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  // Fetch summary stats
  const { data: summary } = useQuery<SummaryStats>({
    queryKey: ['admin-summary'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/stats/summary`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch AI logs
  const { data: aiLogsData } = useQuery({
    queryKey: ['admin-ai-logs', aiLogsGameIdFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '100' });
      if (aiLogsGameIdFilter) {
        params.append('game_id', aiLogsGameIdFilter);
      }
      const response = await axios.get(`${API_BASE_URL}/admin/ai-logs?${params}`);
      return response.data;
    },
    refetchInterval: activeTab === 'ai-logs' ? 10000 : 30000, // Faster refresh when viewing
  });

  // Fetch games
  const { data: gamesData } = useQuery({
    queryKey: ['admin-games'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/games?limit=50`);
      return response.data;
    },
    refetchInterval: activeTab === 'games' ? 10000 : 30000,
  });

  // Fetch playbacks
  const { data: playbacksData } = useQuery({
    queryKey: ['admin-playbacks'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/game-playbacks?limit=30`);
      return response.data;
    },
    refetchInterval: activeTab === 'playbacks' ? 10000 : 30000,
  });

  // Fetch users
  const { data: usersData } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/users?limit=50`);
      return response.data;
    },
    refetchInterval: activeTab === 'users' ? 10000 : 30000,
  });

  // Fetch simulation decks
  const { data: simulationDecks } = useQuery<SimulationDeck[]>({
    queryKey: ['simulation-decks'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/simulation/decks`);
      return response.data;
    },
    enabled: activeTab === 'simulation',
  });

  // Fetch supported models
  const { data: supportedModels } = useQuery<string[]>({
    queryKey: ['simulation-models'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/simulation/models`);
      return response.data;
    },
    enabled: activeTab === 'simulation',
  });

  // Fetch simulation runs
  const { data: simulationRuns, refetch: refetchSimulationRuns } = useQuery<SimulationRun[]>({
    queryKey: ['simulation-runs'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/simulation/runs?limit=20`);
      return response.data;
    },
    refetchInterval: activeTab === 'simulation' ? 5000 : 30000,
    enabled: activeTab === 'simulation',
  });

  // Group AI logs by turn for v3 display
  interface TurnGroup {
    key: string;
    game_id: string;
    turn_number: number;
    player_id: string;
    model_name: string;
    prompts_version: string;
    ai_version: number;
    turn_plan: AILog['turn_plan'];
    created_at: string;
    logs: AILog[];
    has_fallback: boolean;
    fallback_reason: string | null;
  }

  const groupLogsByTurn = (logs: AILog[]): (TurnGroup | AILog)[] => {
    const v3Groups = new Map<string, TurnGroup>();
    const v2Logs: AILog[] = [];

    for (const log of logs) {
      if (log.ai_version === 3 && log.turn_plan) {
        const key = `${log.game_id}-${log.turn_number}-${log.player_id}`;
        if (!v3Groups.has(key)) {
          v3Groups.set(key, {
            key,
            game_id: log.game_id,
            turn_number: log.turn_number,
            player_id: log.player_id,
            model_name: log.model_name,
            prompts_version: log.prompts_version,
            ai_version: 3,
            turn_plan: log.turn_plan,
            created_at: log.created_at,
            logs: [],
            has_fallback: false,
            fallback_reason: null,
          });
        }
        const group = v3Groups.get(key)!;
        group.logs.push(log);
        if (log.plan_execution_status === 'fallback') {
          group.has_fallback = true;
          group.fallback_reason = log.fallback_reason;
        }
      } else {
        v2Logs.push(log);
      }
    }

    // Combine and sort by created_at (most recent first)
    const result: (TurnGroup | AILog)[] = [...v3Groups.values(), ...v2Logs];
    result.sort((a, b) => {
      const aDate = 'logs' in a ? a.created_at : a.created_at;
      const bDate = 'logs' in b ? b.created_at : b.created_at;
      return new Date(bDate).getTime() - new Date(aDate).getTime();
    });

    return result;
  };

  const toggleTurnExpanded = (key: string) => {
    setExpandedTurns(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (startDate: string, endDate: string | null) => {
    if (!endDate) return 'In progress';
    const start = new Date(startDate);
    const end = new Date(endDate);
    const durationMs = end.getTime() - start.getTime();
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const formatRelativeTime = (dateString: string | null) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

  const loadPlaybackDetails = async (gameId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/game-playbacks/${gameId}`);
      setSelectedPlayback(response.data);
    } catch (error) {
      console.error('Failed to load playback details:', error);
      alert('Failed to load playback details');
    }
  };

  const viewAILogsForGame = (gameId: string) => {
    setAiLogsGameIdFilter(gameId);
    setActiveTab('ai-logs');
  };

  const clearAILogsFilter = () => {
    setAiLogsGameIdFilter(null);
  };

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
    
    setIsRunningSimulation(true);
    setRunProgress(null);
    pollErrorCountRef.current = 0; // Reset error count
    
    try {
      // Start simulation (returns immediately with run_id)
      const response = await axios.post(`${API_BASE_URL}/admin/simulation/start`, {
        deck_names: selectedDecks,
        player1_model: player1Model,
        player2_model: player2Model,
        iterations_per_matchup: iterationsPerMatchup,
        max_turns: 40,
      });
      
      const runId = response.data.run_id;
      setActiveRunId(runId);
      setRunProgress({
        completed: 0,
        total: response.data.total_games,
        status: 'pending',
      });
      
      // Poll for progress until completed (with cleanup ref)
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusResponse = await axios.get(
            `${API_BASE_URL}/admin/simulation/runs/${runId}`
          );
          const status = statusResponse.data;
          pollErrorCountRef.current = 0; // Reset on success
          
          setRunProgress({
            completed: status.completed_games,
            total: status.total_games,
            status: status.status,
          });
          
          // Check if simulation is done
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsRunningSimulation(false);
            setActiveRunId(null);
            
            if (status.status === 'completed') {
              // Load full results
              const resultsResponse = await axios.get(
                `${API_BASE_URL}/admin/simulation/runs/${runId}/results`
              );
              setSelectedSimulation(resultsResponse.data);
            } else {
              alert(`Simulation ${status.status}: ${status.error_message || 'Unknown error'}`);
            }
            
            refetchSimulationRuns();
          }
        } catch (pollError) {
          console.error('Error polling simulation status:', pollError);
          pollErrorCountRef.current += 1;
          
          // Stop polling after too many consecutive errors
          if (pollErrorCountRef.current >= MAX_POLL_ERRORS) {
            console.error(`Stopping polling after ${MAX_POLL_ERRORS} consecutive errors`);
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsRunningSimulation(false);
            alert('Lost connection to server. Please refresh and check simulation status.');
          }
        }
      }, 3000); // Poll every 3 seconds
      
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
      const response = await axios.get(`${API_BASE_URL}/admin/simulation/runs/${runId}/results`);
      setSelectedSimulation(response.data);
      setSelectedGameDetail(null); // Clear any game detail when switching runs
    } catch (error) {
      console.error('Failed to load simulation results:', error);
      alert('Failed to load simulation results');
    }
  };

  const loadGameDetail = async (runId: number, gameNumber: number) => {
    setLoadingGameDetail(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/simulation/runs/${runId}/games/${gameNumber}`);
      setSelectedGameDetail(response.data);
    } catch (error) {
      console.error('Failed to load game detail:', error);
      alert('Failed to load game detail');
    } finally {
      setLoadingGameDetail(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white" style={{ padding: 'var(--spacing-component-lg)' }}>
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold" style={{ marginBottom: 'var(--spacing-component-lg)' }}>GGLTCG Admin Data Viewer</h1>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-lg)' }}>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-gray-400 text-xs" style={{ marginBottom: '4px' }}>Total Users</h3>
              <p className="text-2xl font-bold">{summary.users.total}</p>
            </div>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-gray-400 text-xs" style={{ marginBottom: '4px' }}>Games</h3>
              <p className="text-2xl font-bold">{summary.games.total}</p>
              <p className="text-xs text-gray-400" style={{ marginTop: '4px' }}>
                {summary.games.active} active · {summary.games.completed} completed
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-gray-400 text-xs" style={{ marginBottom: '4px' }}>AI Logs</h3>
              <p className="text-2xl font-bold">{summary.ai_logs.total}</p>
              <p className="text-xs text-gray-400" style={{ marginTop: '4px' }}>
                {summary.ai_logs.recent_1h} in last hour
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
              <h3 className="text-gray-400 text-xs" style={{ marginBottom: '4px' }}>Playbacks</h3>
              <p className="text-2xl font-bold">{summary.playbacks.total}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-700" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-lg)' }}>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'summary'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('summary')}
          >
            Summary
          </button>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'ai-logs'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('ai-logs')}
          >
            AI Logs ({aiLogsData?.count || 0})
          </button>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'games'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('games')}
          >
            Games ({gamesData?.count || 0})
          </button>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'playbacks'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('playbacks')}
          >
            Playbacks ({playbacksData?.count || 0})
          </button>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'users'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('users')}
          >
            Users ({usersData?.count || 0})
          </button>
          <button
            className={`px-4 py-2 font-semibold ${
              activeTab === 'simulation'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setActiveTab('simulation')}
          >
            Simulation
          </button>
        </div>

        {/* Content */}
        {activeTab === 'summary' && (
          <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
            <h2 className="text-2xl font-bold" style={{ marginBottom: 'var(--spacing-component-md)' }}>Database Overview</h2>
            <p className="text-gray-400" style={{ marginBottom: 'var(--spacing-component-md)' }}>
              Use the tabs above to view AI decision logs, game data, and playback recordings.
            </p>
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
              <div>
                <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Recent Activity (Last 24h)</h3>
                <p className="text-gray-400">{summary?.games.recent_24h || 0} games started</p>
              </div>
              <div>
                <h3 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>AI Activity (Last Hour)</h3>
                <p className="text-gray-400">{summary?.ai_logs.recent_1h || 0} AI decisions logged</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai-logs' && (
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
              {aiLogsGameIdFilter ? (
                <div className="flex justify-between items-center">
                  <p className="text-sm">
                    <span className="text-purple-400 font-semibold">Filtered by Game: </span>
                    <span className="text-gray-300 font-mono">{aiLogsGameIdFilter}</span>
                    <span className="text-gray-400"> ({aiLogsData?.count || 0} logs)</span>
                  </p>
                  <button
                    onClick={clearAILogsFilter}
                    className="bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
                    style={{ padding: '4px var(--spacing-component-sm)' }}
                  >
                    Clear Filter
                  </button>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  Showing {aiLogsData?.count || 0} most recent AI decisions (v3 grouped by turn)
                </p>
              )}
            </div>
            {aiLogsData?.logs && groupLogsByTurn(aiLogsData.logs).map((item) => {
              // V3 Turn Group
              if ('logs' in item) {
                const turnGroup = item;
                const isExpanded = expandedTurns.has(turnGroup.key);
                const completedActions = turnGroup.logs.length;
                const totalActions = turnGroup.turn_plan?.total_actions || completedActions;
                const planCompleted = completedActions === totalActions && !turnGroup.has_fallback;
                
                return (
                  <div key={turnGroup.key} className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
                    {/* Compact Turn Header */}
                    <div 
                      className="flex justify-between items-center cursor-pointer"
                      onClick={() => toggleTurnExpanded(turnGroup.key)}
                    >
                      <div className="flex items-center flex-wrap" style={{ gap: 'var(--spacing-component-sm)' }}>
                        <span className="text-xs rounded bg-purple-600" style={{ padding: '2px var(--spacing-component-xs)' }}>v3</span>
                        <span className="font-semibold">Turn {turnGroup.turn_number}</span>
                        <span className="text-gray-400 text-sm">Game: {turnGroup.game_id.substring(0, 8)}...</span>
                        <span className="text-gray-500 text-sm">{turnGroup.model_name}</span>
                        {planCompleted ? (
                          <span className="text-xs rounded bg-green-600" style={{ padding: '2px var(--spacing-component-xs)' }}>
                            ✓ {completedActions} actions
                          </span>
                        ) : turnGroup.has_fallback ? (
                          <span className="text-xs rounded bg-yellow-600" style={{ padding: '2px var(--spacing-component-xs)' }}>
                            ⚠ Fallback after {completedActions}/{totalActions}
                          </span>
                        ) : (
                          <span className="text-xs rounded bg-blue-600" style={{ padding: '2px var(--spacing-component-xs)' }}>
                            {completedActions}/{totalActions} actions
                          </span>
                        )}
                      </div>
                      <span className="text-gray-400">{isExpanded ? '▼' : '▶'}</span>
                    </div>
                    
                    {/* Expanded Turn Details */}
                    {isExpanded && turnGroup.turn_plan && (
                      <div style={{ marginTop: 'var(--spacing-component-md)' }}>
                        {/* Strategy */}
                        <div className="bg-gray-900 rounded" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                          <span className="text-purple-400 font-semibold">Strategy: </span>
                          <span className="text-gray-300">{turnGroup.turn_plan.strategy}</span>
                        </div>
                        
                        {/* Turn Metrics */}
                        <div className="flex flex-wrap text-sm" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-sm)' }}>
                          <span><span className="text-gray-500">CC:</span> {turnGroup.turn_plan.cc_start} → {turnGroup.turn_plan.cc_after_plan}</span>
                          <span><span className="text-gray-500">Target:</span> Sleep {turnGroup.turn_plan.expected_cards_slept} cards</span>
                          {turnGroup.turn_plan.cc_efficiency && (
                            <span><span className="text-gray-500">Efficiency:</span> {turnGroup.turn_plan.cc_efficiency}</span>
                          )}
                        </div>
                        
                        {/* Fallback Warning */}
                        {turnGroup.has_fallback && turnGroup.fallback_reason && (
                          <div className="bg-yellow-900/30 border border-yellow-600 rounded text-sm" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                            <span className="text-yellow-400 font-semibold">⚠️ Fallback: </span>
                            <span className="text-yellow-200">{turnGroup.fallback_reason}</span>
                          </div>
                        )}
                        
                        {/* Planned Action Sequence (from first log with action_sequence) */}
                        {turnGroup.turn_plan.action_sequence && turnGroup.turn_plan.action_sequence.length > 0 && (
                          <div className="text-sm" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                            <span className="text-gray-500">Planned actions:</span>
                            <ol className="list-decimal list-inside" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                              {turnGroup.turn_plan.action_sequence.map((action, idx) => {
                                // Find execution log entry for this action
                                const execLog = turnGroup.turn_plan?.execution_log?.find(log => log.action_index === idx);
                                // Only show success if execution was explicitly confirmed
                                const isSuccess = execLog?.status === 'success' && execLog?.execution_confirmed === true;
                                const isMatchedButNotExecuted = execLog?.status === 'success' && execLog?.execution_confirmed !== true;
                                const isExecutionFailed = execLog?.status === 'execution_failed';
                                const isMatchFailed = execLog?.status === 'failed';
                                const isLLMFallback = execLog?.status === 'fallback_to_llm' && execLog?.method === 'llm';
                                const notAttempted = !execLog; // No log entry means never attempted
                                
                                return (
                                  <li key={idx} className={notAttempted ? "text-gray-500" : "text-gray-300"}>
                                    {/* Execution status indicator */}
                                    {isSuccess && <span className="text-green-400">✅ </span>}
                                    {isMatchedButNotExecuted && <span className="text-yellow-600">⚠️ </span>}
                                    {(isExecutionFailed || isMatchFailed) && <span className="text-red-400">❌ </span>}
                                    {isLLMFallback && <span className="text-yellow-400">⚠️ </span>}
                                    {notAttempted && <span className="text-gray-600">⊘ </span>}
                                    
                                    <span className="text-blue-400">{action.action_type}</span>
                                    {action.card_name && <span> {action.card_name}</span>}
                                    {action.target_names && action.target_names.length > 0 && (
                                      <span className="text-gray-400"> → {action.target_names.join(', ')}</span>
                                    )}
                                    <span className="text-gray-500"> ({action.cc_cost} CC)</span>
                                    
                                    {/* Matched but not executed */}
                                    {isMatchedButNotExecuted && (
                                      <span className="text-yellow-600 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                        ⚠️ Matched to available action but execution not confirmed
                                      </span>
                                    )}
                                    
                                    {/* Not attempted indicator */}
                                    {notAttempted && (
                                      <span className="text-gray-600 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                        Plan execution stopped before this action
                                      </span>
                                    )}
                                    
                                    {/* Execution failure reason - show for any failure */}
                                    {execLog?.reason && (isExecutionFailed || isMatchFailed) && (
                                      <span className="text-red-300 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                        ❌ {isExecutionFailed ? 'Execution failed: ' : 'Match failed: '}{execLog.reason}
                                      </span>
                                    )}
                                    
                                    {action.reasoning && !notAttempted && (
                                      <span className="text-gray-500 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                        {action.reasoning}
                                      </span>
                                    )}
                                  </li>
                                );
                              })}
                            </ol>
                          </div>
                        )}
                        
                        {/* Planning Prompt (collapsible) */}
                        {turnGroup.turn_plan.planning_prompt && (
                          <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                            <summary className="text-gray-500 cursor-pointer hover:text-gray-300">
                              View planning prompt ({turnGroup.turn_plan.planning_prompt.length} chars)
                            </summary>
                            <pre className="bg-gray-900 rounded overflow-x-auto text-xs text-gray-400 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                              {turnGroup.turn_plan.planning_prompt}
                            </pre>
                          </details>
                        )}
                        
                        {/* Planning Response (TurnPlan JSON - collapsible) */}
                        {turnGroup.turn_plan.planning_response && (
                          <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                            <summary className="text-gray-500 cursor-pointer hover:text-gray-300">
                              View planning response ({turnGroup.turn_plan.planning_response.length} chars)
                            </summary>
                            <pre className="bg-gray-900 rounded overflow-x-auto text-xs text-gray-400 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                              {turnGroup.turn_plan.planning_response}
                            </pre>
                          </details>
                        )}
                        
                        {/* Executed actions (from logs - fallback if no action_sequence) */}
                        {(!turnGroup.turn_plan.action_sequence || turnGroup.turn_plan.action_sequence.length === 0) && (
                          <div className="text-sm">
                            <span className="text-gray-500">Actions executed:</span>
                            <ol className="list-decimal list-inside" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                              {turnGroup.logs
                                .sort((a, b) => (a.turn_plan?.current_action || 0) - (b.turn_plan?.current_action || 0))
                                .map((log) => (
                                  <li key={log.id} className="text-gray-300">
                                    {log.reasoning || `Action #${log.turn_plan?.current_action || '?'}`}
                                    {log.plan_execution_status === 'fallback' && (
                                      <span className="text-yellow-400 text-xs" style={{ marginLeft: 'var(--spacing-component-xs)' }}>(fallback)</span>
                                    )}
                                  </li>
                                ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              }
              
              // V2 Individual Log (unchanged display)
              const log = item;
              return (
                <div key={log.id} className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)' }}>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center flex-wrap" style={{ gap: 'var(--spacing-component-sm)' }}>
                        <span className="text-xs rounded bg-gray-600" style={{ padding: '2px var(--spacing-component-xs)' }}>v2</span>
                        <span className="font-semibold">Turn {log.turn_number}</span>
                        <span className="text-gray-400 text-sm">Game: {log.game_id.substring(0, 8)}...</span>
                        <span className="text-gray-500 text-sm">{log.model_name}</span>
                      </div>
                      <p className="text-sm text-gray-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                        {formatDate(log.created_at)}
                      </p>
                    </div>
                    <button
                      className="bg-blue-600 hover:bg-blue-700 rounded text-sm"
                      style={{ padding: '4px var(--spacing-component-sm)' }}
                      onClick={() => setSelectedLog(selectedLog?.id === log.id ? null : log)}
                    >
                      {selectedLog?.id === log.id ? 'Hide' : 'Details'}
                    </button>
                  </div>
                  
                  {selectedLog?.id === log.id && (
                    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-md)' }}>
                      {log.reasoning && (
                        <div>
                          <span className="text-gray-500 text-sm">Reasoning: </span>
                          <span className="text-gray-300 text-sm">{log.reasoning}</span>
                        </div>
                      )}
                      {log.prompt && (
                        <div>
                          <h4 className="font-semibold text-sm" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Prompt:</h4>
                          <pre className="bg-gray-900 rounded overflow-x-auto text-xs text-gray-300 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', maxHeight: '200px', overflow: 'auto' }}>
                            {log.prompt}
                          </pre>
                        </div>
                      )}
                      {log.response && (
                        <div>
                          <h4 className="font-semibold text-sm" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Response:</h4>
                          <pre className="bg-gray-900 rounded overflow-x-auto text-xs text-gray-300 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)' }}>
                            {log.response}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'games' && (
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
              <p className="text-gray-400 text-sm">
                Showing {gamesData?.count || 0} most recent games
              </p>
            </div>
            {gamesData?.games.map((game: Game) => (
              <div key={game.id} className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-xl font-semibold">
                      {game.player1_name} vs {game.player2_name}
                      <span className={`text-xs rounded ${
                        game.status === 'active' ? 'bg-green-600' :
                        game.status === 'completed' ? 'bg-blue-600' :
                        'bg-gray-600'
                      }`} style={{ marginLeft: 'var(--spacing-component-sm)', padding: '4px var(--spacing-component-xs)' }}>
                        {game.status}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-400 font-mono" style={{ marginTop: '4px' }}>
                      Game ID: {game.id}
                      {game.game_code && ` · Code: ${game.game_code}`}
                    </p>
                    <p className="text-sm text-gray-400">
                      Turn {game.turn_number} · {game.phase} Phase
                    </p>
                    <p className="text-sm text-gray-400">
                      Created: {formatDate(game.created_at)} · Updated: {formatDate(game.updated_at)}
                    </p>
                    {game.winner_id && (
                      <p className="text-sm text-green-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                        Winner: {game.winner_id === game.player1_id ? game.player1_name : game.player2_name}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'playbacks' && (
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
              <p className="text-gray-400 text-sm">
                Showing {playbacksData?.count || 0} most recent completed games
              </p>
            </div>
            {selectedPlayback ? (
              <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
                <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <button
                    onClick={() => setSelectedPlayback(null)}
                    className="bg-blue-600 hover:bg-blue-700 text-white rounded"
                    style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
                  >
                    ← Back to Playbacks List
                  </button>
                  <button
                    onClick={() => viewAILogsForGame(selectedPlayback.game_id)}
                    className="bg-purple-600 hover:bg-purple-700 text-white rounded"
                    style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
                  >
                    View AI Logs for this Game →
                  </button>
                </div>
                <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                  {/* Header - Player vs Player */}
                  <h2 className="text-2xl font-bold" style={{ marginBottom: 'var(--spacing-component-md)' }}>
                    {selectedPlayback.player1_name} vs {selectedPlayback.player2_name}
                  </h2>

                  {/* Winner and Game Stats - Prominent */}
                  <div style={{ marginBottom: 'var(--spacing-component-xs)' }}>
                    <span className="text-xl font-bold">Game winner: </span>
                    <span className="text-xl font-bold text-green-400">
                      {selectedPlayback.winner_id === selectedPlayback.player1_id
                        ? selectedPlayback.player1_name
                        : selectedPlayback.player2_name}
                    </span>
                    <span className="text-xl">, in {selectedPlayback.turn_count} turns, {formatDuration(selectedPlayback.created_at, selectedPlayback.completed_at)}.</span>
                  </div>
                  
                  {/* Game ID and Timestamp - Discrete */}
                  <div className="text-sm text-gray-500" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
                    (Game ID: {selectedPlayback.game_id}, Completed: {formatDate(selectedPlayback.completed_at || '')})
                  </div>

                  {/* Starting Decks - Table Format */}
                  <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                    <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Starting Decks</h3>
                    <div className="bg-gray-900 rounded overflow-hidden">
                      <table className="w-full text-sm">
                        <tbody>
                          <tr className="border-b border-gray-700">
                            <td className="px-4 py-3 font-semibold bg-gray-950 whitespace-nowrap">
                              {selectedPlayback.player1_name}
                              {selectedPlayback.first_player_id === selectedPlayback.player1_id && (
                                <span className="text-xs text-yellow-400" style={{ marginLeft: 'var(--spacing-component-xs)' }}>(**first**)</span>
                              )}
                            </td>
                            {[...selectedPlayback.starting_deck_p1].sort().map((card, idx) => (
                              <td key={idx} className="px-4 py-3 text-center">
                                {card}
                              </td>
                            ))}
                          </tr>
                          <tr>
                            <td className="px-4 py-3 font-semibold bg-gray-950 whitespace-nowrap">
                              {selectedPlayback.player2_name}
                              {selectedPlayback.first_player_id === selectedPlayback.player2_id && (
                                <span className="text-xs text-yellow-400" style={{ marginLeft: 'var(--spacing-component-xs)' }}>(**first**)</span>
                              )}
                            </td>
                            {[...selectedPlayback.starting_deck_p2].sort().map((card, idx) => (
                              <td key={idx} className="px-4 py-3 text-center">
                                {card}
                              </td>
                            ))}
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* CC Tracking with Actions - Compact timeline view like Simulation */}
                  {selectedPlayback.cc_tracking && selectedPlayback.cc_tracking.length > 0 && (
                    <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                      <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Turn-by-Turn Summary</h3>
                      <div className="bg-gray-900 rounded overflow-x-auto">
                        <table className="w-full text-sm border-collapse">
                          <thead className="bg-gray-950">
                            <tr>
                              <th className="px-3 py-2 text-center border-b border-gray-700 w-16">Turn</th>
                              <th className="px-3 py-2 text-center text-green-400 border-b border-gray-700 w-24">
                                {selectedPlayback.player1_name.length > 8 ? 'P1' : selectedPlayback.player1_name} CC
                              </th>
                              <th className="px-3 py-2 text-center text-blue-400 border-b border-gray-700 w-24">
                                {selectedPlayback.player2_name.length > 8 ? 'P2' : selectedPlayback.player2_name} CC
                              </th>
                              <th className="px-3 py-2 text-left border-b border-gray-700">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(() => {
                              // Group CC tracking by turn, using actual player IDs
                              const p1Id = selectedPlayback.player1_id;
                              const p2Id = selectedPlayback.player2_id;
                              const turnMap = new Map<number, { p1?: TurnCC, p2?: TurnCC }>();
                              selectedPlayback.cc_tracking!.forEach(cc => {
                                if (!turnMap.has(cc.turn)) turnMap.set(cc.turn, {});
                                const entry = turnMap.get(cc.turn)!;
                                if (cc.player_id === p1Id) entry.p1 = cc;
                                else if (cc.player_id === p2Id) entry.p2 = cc;
                              });
                              const turns = Array.from(turnMap.keys()).sort((a, b) => a - b);
                              
                              // Group play-by-play actions by turn
                              const actionsByTurn = new Map<number, typeof selectedPlayback.play_by_play>();
                              selectedPlayback.play_by_play?.forEach(action => {
                                if (!actionsByTurn.has(action.turn)) actionsByTurn.set(action.turn, []);
                                actionsByTurn.get(action.turn)!.push(action);
                              });
                              
                              // Format CC: simple start-spent→end format
                              const formatCC = (data: TurnCC | undefined, isActive: boolean): React.ReactNode => {
                                if (!data) return <span className="text-gray-600">—</span>;
                                return (
                                  <span className={`font-mono ${isActive ? '' : 'opacity-60'}`}>
                                    {data.cc_start}
                                    {data.cc_gained > 0 && <span className="text-yellow-400">+{data.cc_gained}</span>}
                                    {data.cc_spent > 0 && <span className="text-red-400">-{data.cc_spent}</span>}
                                    <span className="text-gray-500">→</span>
                                    <span className="font-bold">{data.cc_end}</span>
                                  </span>
                                );
                              };
                              
                              return turns.map(turn => {
                                const data = turnMap.get(turn)!;
                                const turnActions = actionsByTurn.get(turn) || [];
                                const isP1Turn = turn % 2 === 1;
                                
                                // Filter out end_turn actions for cleaner display
                                const visibleActions = turnActions.filter(a => a.action_type !== 'end_turn');
                                
                                return (
                                  <tr key={turn} className="border-t border-gray-800 hover:bg-gray-850">
                                    <td className="px-3 py-2 text-center font-bold">{turn}</td>
                                    <td className={`px-3 py-2 text-center ${isP1Turn ? 'bg-green-900/20' : ''}`}>
                                      {formatCC(data.p1, isP1Turn)}
                                    </td>
                                    <td className={`px-3 py-2 text-center ${!isP1Turn ? 'bg-blue-900/20' : ''}`}>
                                      {formatCC(data.p2, !isP1Turn)}
                                    </td>
                                    <td className="px-3 py-2 text-left text-xs">
                                      {visibleActions.slice(0, 8).map((a, i) => (
                                        <React.Fragment key={i}>
                                          {i > 0 && <span className="text-gray-600">, </span>}
                                          <span className={a.player === selectedPlayback.player1_name ? 'text-green-400' : 'text-blue-400'}>
                                            {a.description}
                                          </span>
                                        </React.Fragment>
                                      ))}
                                      {visibleActions.length > 8 && <span className="text-gray-500"> +{visibleActions.length - 8} more</span>}
                                    </td>
                                  </tr>
                                );
                              });
                            })()}
                            {/* Summary row */}
                            {(() => {
                              const p1Id = selectedPlayback.player1_id;
                              const p2Id = selectedPlayback.player2_id;
                              const p1Gained = selectedPlayback.cc_tracking!.filter(cc => cc.player_id === p1Id).reduce((sum, cc) => sum + cc.cc_gained, 0);
                              const p1Spent = selectedPlayback.cc_tracking!.filter(cc => cc.player_id === p1Id).reduce((sum, cc) => sum + cc.cc_spent, 0);
                              const p2Gained = selectedPlayback.cc_tracking!.filter(cc => cc.player_id === p2Id).reduce((sum, cc) => sum + cc.cc_gained, 0);
                              const p2Spent = selectedPlayback.cc_tracking!.filter(cc => cc.player_id === p2Id).reduce((sum, cc) => sum + cc.cc_spent, 0);
                              return (
                                <tr className="border-t border-gray-700 bg-gray-900/50">
                                  <td className="px-3 py-2 text-center text-xs text-gray-400">Total</td>
                                  <td className="px-3 py-2 text-center text-green-400 text-xs">
                                    <span className="text-yellow-400">+{p1Gained}</span>
                                    <span className="text-red-400">·{p1Spent}</span>
                                  </td>
                                  <td className="px-3 py-2 text-center text-blue-400 text-xs">
                                    <span className="text-yellow-400">+{p2Gained}</span>
                                    <span className="text-red-400">·{p2Spent}</span>
                                  </td>
                                  <td></td>
                                </tr>
                              );
                            })()}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Play-by-Play */}
                  <div>
                    <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Play-by-Play</h3>
                    <div className="bg-gray-900 rounded overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-950">
                          <tr>
                            <th className="px-4 py-2 text-left">Turn</th>
                            <th className="px-4 py-2 text-left">Player</th>
                            <th className="px-4 py-2 text-left">Action</th>
                            <th className="px-4 py-2 text-left">Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedPlayback.play_by_play.map((entry, index) => (
                            <tr key={index} className="border-t border-gray-800">
                              <td className="px-4 py-2">{entry.turn}</td>
                              <td className="px-4 py-2">{entry.player}</td>
                              <td className="px-4 py-2">{entry.action_type}</td>
                              <td className="px-4 py-2">{entry.description}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              playbacksData?.games.map((playback: GamePlayback) => (
                <div key={playback.id} className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                  <h3 className="text-xl font-semibold">
                    {playback.player1_name} vs {playback.player2_name}
                  </h3>
                  <p className="text-sm text-gray-400 font-mono" style={{ marginTop: '4px' }}>
                    Game ID: {playback.game_id}
                  </p>
                  <p className="text-sm text-gray-400">
                    {playback.turn_count} turns · {formatDuration(playback.created_at, playback.completed_at)}
                  </p>
                  {playback.winner_id && (
                    <p className="text-sm text-green-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                      Winner: {playback.winner_id === playback.player1_id ? playback.player1_name : playback.player2_name}
                    </p>
                  )}
                  <p className="text-sm text-gray-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                    Completed: {playback.completed_at ? formatDate(playback.completed_at) : 'In progress'}
                  </p>
                  <button
                    onClick={() => loadPlaybackDetails(playback.game_id)}
                    className="inline-block bg-blue-600 hover:bg-blue-700 rounded text-sm"
                    style={{ marginTop: 'var(--spacing-component-sm)', padding: '4px var(--spacing-component-sm)' }}
                  >
                    View Playback Details
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
            <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
              <p className="text-gray-400 text-sm">
                Showing {usersData?.count || 0} registered users
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-950">
                  <tr>
                    <th className="px-4 py-3 text-left">Display Name</th>
                    <th className="px-4 py-3 text-left">First Name</th>
                    <th className="px-4 py-3 text-right">Games</th>
                    <th className="px-4 py-3 text-right">Wins</th>
                    <th className="px-4 py-3 text-right">Win Rate</th>
                    <th className="px-4 py-3 text-right">Avg Turns</th>
                    <th className="px-4 py-3 text-right">Avg Game</th>
                    <th className="px-4 py-3 text-left">Deck 1</th>
                    <th className="px-4 py-3 text-left">Deck 2</th>
                    <th className="px-4 py-3 text-left">Deck 3</th>
                    <th className="px-4 py-3 text-left">Last Game</th>
                    <th className="px-4 py-3 text-left">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {usersData?.users.map((user: User) => (
                    <tr key={user.google_id} className="border-t border-gray-700 hover:bg-gray-750">
                      <td className="px-4 py-3 font-semibold">{user.display_name}</td>
                      <td className="px-4 py-3 text-gray-400">{user.first_name}</td>
                      <td className="px-4 py-3 text-right">{user.games_played}</td>
                      <td className="px-4 py-3 text-right">{user.games_won}</td>
                      <td className="px-4 py-3 text-right">
                        {user.games_played > 0 ? (
                          <span className={user.win_rate >= 50 ? 'text-green-400' : 'text-gray-300'}>
                            {user.win_rate.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {user.games_played > 0 && user.avg_turns ? (
                          <span className="text-orange-400">{user.avg_turns.toFixed(1)}</span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {user.games_played > 0 && user.avg_game_duration_seconds ? (
                          <span className="text-cyan-400">
                            {user.avg_game_duration_seconds < 60 
                              ? `${Math.round(user.avg_game_duration_seconds)}s`
                              : `${Math.floor(user.avg_game_duration_seconds / 60)}m ${Math.round(user.avg_game_duration_seconds % 60)}s`
                            }
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-300">
                        {user.favorite_decks?.[0]?.length > 0 ? user.favorite_decks[0].join(', ') : '-'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-300">
                        {user.favorite_decks?.[1]?.length > 0 ? user.favorite_decks[1].join(', ') : '-'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-300">
                        {user.favorite_decks?.[2]?.length > 0 ? user.favorite_decks[2].join(', ') : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {user.last_game_at ? (
                          <div>
                            <div className="text-gray-300">{formatRelativeTime(user.last_game_at)}</div>
                            {user.last_game_status && (
                              <div className={`text-xs ${
                                user.last_game_status === 'completed' ? 'text-blue-400' :
                                user.last_game_status === 'active' ? 'text-green-400' :
                                'text-gray-500'
                              }`}>
                                {user.last_game_status}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-500">Never</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{formatRelativeTime(user.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'simulation' && (
          <div className="flex flex-col" style={{ gap: 'var(--spacing-component-lg)' }}>
            {/* Configuration Panel */}
            {!selectedSimulation && (
              <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                <h2 className="text-2xl font-bold" style={{ marginBottom: 'var(--spacing-component-md)' }}>
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
                            : 'border-gray-600 bg-gray-900 hover:border-gray-500'
                        }`}
                        style={{ padding: 'var(--spacing-component-md)' }}
                        onClick={() => toggleDeckSelection(deck.name)}
                      >
                        <div className="font-semibold">{deck.name}</div>
                        <div className="text-xs text-gray-400" style={{ marginTop: '4px' }}>
                          {deck.description}
                        </div>
                        <div className="text-xs text-gray-500" style={{ marginTop: '4px' }}>
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
                      className="w-full bg-gray-900 border border-gray-600 rounded text-white"
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
                      className="w-full bg-gray-900 border border-gray-600 rounded text-white"
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
                            <span className="text-gray-400">
                              {numMatchups} matchups ({numDecks}² = mirrors + both directions) × {iterationsPerMatchup} games ={' '}
                            </span>
                            <span className={`font-semibold ${exceedsLimit ? 'text-red-400' : 'text-white'}`}>
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

                {/* Start Button */}
                {(() => {
                  const totalGames = selectedDecks.length * selectedDecks.length * iterationsPerMatchup;
                  const MAX_GAMES = 500;
                  const exceedsLimit = totalGames > MAX_GAMES;
                  const isDisabled = isRunningSimulation || selectedDecks.length < 1 || exceedsLimit;
                  
                  return (
                    <button
                      onClick={startSimulation}
                      disabled={isDisabled}
                      className={`w-full rounded font-semibold ${
                        isDisabled
                          ? 'bg-gray-600 cursor-not-allowed'
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
                        Simulation {runProgress.status === 'pending' ? 'starting' : 'in progress'}...
                      </span>
                      <span className="text-blue-400">
                        {runProgress.completed} / {runProgress.total} games
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-3">
                      <div 
                        className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                        style={{ width: `${runProgress.total > 0 ? (runProgress.completed / runProgress.total * 100) : 0}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-400" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                      {runProgress.total > 0 ? Math.round(runProgress.completed / runProgress.total * 100) : 0}% complete 
                      {activeRunId && <span> (Run #{activeRunId})</span>}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Results Panel */}
            {selectedSimulation && (
              <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
                <button
                  onClick={() => setSelectedSimulation(null)}
                  className="bg-blue-600 hover:bg-blue-700 text-white rounded"
                  style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)', alignSelf: 'flex-start' }}
                >
                  ← Back to Configuration
                </button>
                
                <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                  <h2 className="text-2xl font-bold" style={{ marginBottom: 'var(--spacing-component-md)' }}>
                    Simulation Results
                    <span className={`text-sm rounded ${
                      selectedSimulation.status === 'completed' ? 'bg-green-600' :
                      selectedSimulation.status === 'running' ? 'bg-yellow-600' :
                      selectedSimulation.status === 'failed' ? 'bg-red-600' :
                      'bg-gray-600'
                    }`} style={{ marginLeft: 'var(--spacing-component-sm)', padding: '4px var(--spacing-component-xs)' }}>
                      {selectedSimulation.status}
                    </span>
                  </h2>
                  
                  {/* Config Summary */}
                  <div className="text-sm text-gray-400" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                    <div>Decks: {selectedSimulation.config.deck_names.join(', ')}</div>
                    <div className="bg-gray-900/50 rounded p-2 mt-2">
                      <div className="font-semibold text-white mb-1">Model Assignment:</div>
                      <div className="flex gap-4">
                        <span><span className="text-green-400">Player 1 / Deck 1:</span> {selectedSimulation.config.player1_model}</span>
                        <span><span className="text-blue-400">Player 2 / Deck 2:</span> {selectedSimulation.config.player2_model}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">Note: Player 1 always goes first (receives 2 CC on turn 1 instead of 4)</div>
                    </div>
                    <div style={{ marginTop: '8px' }}>Games: {selectedSimulation.completed_games}/{selectedSimulation.total_games}</div>
                    {selectedSimulation.completed_at && (
                      <div>Completed: {formatDate(selectedSimulation.completed_at)}</div>
                    )}
                  </div>

                  {/* Matchup Results Matrix */}
                  <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                    Matchup Results Matrix
                    <span className="text-sm font-normal text-gray-400 ml-2">(Row Deck as P1 vs Column Deck as P2)</span>
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
                      if (winRate > 0.45) return 'bg-gray-700';
                      if (winRate > 0.3) return 'bg-red-900';
                      return 'bg-red-700';
                    };

                    return (
                      <div className="bg-gray-900 rounded overflow-hidden" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                        <table className="w-full text-sm">
                          <thead className="bg-gray-950">
                            <tr>
                              <th className="px-3 py-2 text-left border-r border-gray-700">
                                <span className="text-green-400">P1 (Row)</span>
                                <span className="text-gray-500"> \ </span>
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
                              <tr key={rowDeck} className="border-t border-gray-800">
                                <td className="px-3 py-2 font-medium text-green-400 border-r border-gray-700">{rowDeck}</td>
                                {deckNames.map(colDeck => {
                                  const stats = matchupMap.get(`${rowDeck}_vs_${colDeck}`);
                                  const isMirror = rowDeck === colDeck;
                                  
                                  if (!stats) {
                                    return (
                                      <td key={colDeck} className={`px-3 py-2 text-center ${isMirror ? 'bg-gray-800' : ''} text-gray-600`}>
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
                        <div className="px-4 py-2 text-xs text-gray-400 border-t border-gray-800">
                          <span className="inline-block w-4 h-3 bg-green-600 mr-1"></span>≥70%
                          <span className="inline-block w-4 h-3 bg-green-800 mx-1 ml-3"></span>55-69%
                          <span className="inline-block w-4 h-3 bg-gray-700 mx-1 ml-3"></span>45-55%
                          <span className="inline-block w-4 h-3 bg-red-900 mx-1 ml-3"></span>31-44%
                          <span className="inline-block w-4 h-3 bg-red-700 mx-1 ml-3"></span>≤30%
                        </div>
                      </div>
                    );
                  })()}

                  {/* Individual Games */}
                  <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                    Individual Games
                    <span className="text-sm font-normal text-gray-400 ml-2">(click to view details)</span>
                  </h3>
                  <div className="bg-gray-900 rounded overflow-hidden max-h-[600px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950 sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-2 text-left">#</th>
                          <th className="px-4 py-2 text-left">Matchup</th>
                          <th className="px-4 py-2 text-center">Result</th>
                          <th className="px-4 py-2 text-center text-green-400" title="Player 1 Total CC Spent">P1 CC</th>
                          <th className="px-4 py-2 text-center text-blue-400" title="Player 2 Total CC Spent">P2 CC</th>
                          <th className="px-4 py-2 text-center">Turns</th>
                          <th className="px-4 py-2 text-center">Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedSimulation.games.map(game => (
                          <React.Fragment key={game.game_number}>
                            <tr 
                              className={`border-t border-gray-800 cursor-pointer hover:bg-gray-800 ${selectedGameDetail?.game_number === game.game_number ? 'bg-gray-700' : ''}`}
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
                                <span className="ml-2 text-gray-500">{selectedGameDetail?.game_number === game.game_number ? '▼' : '▶'}</span>
                              </td>
                              <td className="px-4 py-2">
                                <span className="text-green-400">{game.deck1_name}</span>
                                <span className="text-gray-500"> vs </span>
                                <span className="text-blue-400">{game.deck2_name}</span>
                              </td>
                              <td className="px-4 py-2 text-center">
                                {game.outcome === 'draw' ? (
                                  <span className="text-gray-400">Draw</span>
                                ) : (
                                  <span className={game.outcome === 'player1_win' ? 'text-green-400' : 'text-blue-400'}>
                                    {game.winner_deck} wins
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2 text-center text-green-400">{game.p1_cc_spent}</td>
                              <td className="px-4 py-2 text-center text-blue-400">{game.p2_cc_spent}</td>
                              <td className="px-4 py-2 text-center text-orange-400">{game.turn_count}</td>
                              <td className="px-4 py-2 text-center text-cyan-400">
                                {(game.duration_ms / 1000).toFixed(1)}s
                              </td>
                            </tr>
                            {/* Inline detail panel */}
                            {selectedGameDetail?.game_number === game.game_number && (
                              <tr>
                                <td colSpan={7} className="p-0">
                                  <div className="bg-gray-800 border-l-4 border-blue-500 p-4">
                                    {loadingGameDetail ? (
                                      <div className="text-center text-gray-400 py-4">Loading game details...</div>
                                    ) : selectedGameDetail.cc_tracking && selectedGameDetail.cc_tracking.length > 0 ? (
                                      <div>
                                        <div className="flex justify-between items-center mb-3">
                                          <h4 className="font-semibold">Game #{selectedGameDetail.game_number} Details</h4>
                                        </div>
                                        
                                        {/* CC Tracking - Compact timeline view */}
                                        <div className="overflow-x-auto mb-4">
                                          <table className="w-full text-sm border-collapse">
                                            <thead className="bg-gray-900">
                                              <tr>
                                                <th className="px-3 py-2 text-center border-b border-gray-700 w-16">Turn</th>
                                                <th className="px-3 py-2 text-center text-green-400 border-b border-gray-700 w-32">P1 CC</th>
                                                <th className="px-3 py-2 text-center text-blue-400 border-b border-gray-700 w-32">P2 CC</th>
                                                <th className="px-3 py-2 text-left border-b border-gray-700">Actions</th>
                                              </tr>
                                            </thead>
                                            <tbody>
                                              {(() => {
                                                // Group CC tracking by turn
                                                const turnMap = new Map<number, { p1?: typeof selectedGameDetail.cc_tracking[0], p2?: typeof selectedGameDetail.cc_tracking[0] }>();
                                                selectedGameDetail.cc_tracking.forEach(cc => {
                                                  if (!turnMap.has(cc.turn)) turnMap.set(cc.turn, {});
                                                  const entry = turnMap.get(cc.turn)!;
                                                  if (cc.player_id === 'player1') entry.p1 = cc;
                                                  else entry.p2 = cc;
                                                });
                                                const turns = Array.from(turnMap.keys()).sort((a, b) => a - b);
                                                
                                                // Group actions by turn
                                                const actionsByTurn = new Map<number, typeof selectedGameDetail.action_log>();
                                                selectedGameDetail.action_log?.forEach(action => {
                                                  if (!actionsByTurn.has(action.turn)) actionsByTurn.set(action.turn, []);
                                                  actionsByTurn.get(action.turn)!.push(action);
                                                });
                                                
                                                // Format CC change as compact string with proper spacing
                                                const formatCC = (data: typeof selectedGameDetail.cc_tracking[0] | undefined, isActive: boolean): React.ReactNode => {
                                                  if (!data) return <span className="text-gray-600">—</span>;
                                                  return (
                                                    <span className={`font-mono ${isActive ? '' : 'opacity-60'}`}>
                                                      <span>{data.cc_start}</span>
                                                      {data.cc_gained > 0 && <span className="text-yellow-400 ml-1">+{data.cc_gained}</span>}
                                                      {data.cc_spent > 0 && <span className="text-red-400 ml-1">-{data.cc_spent}</span>}
                                                      <span className="text-gray-500 mx-1">→</span>
                                                      <span className="font-bold">{data.cc_end}</span>
                                                    </span>
                                                  );
                                                };
                                                
                                                return turns.map(turn => {
                                                  const data = turnMap.get(turn)!;
                                                  const turnActions = actionsByTurn.get(turn) || [];
                                                  const isP1Turn = turn % 2 === 1; // Odd turns = P1, even turns = P2
                                                  
                                                  const visibleActions = turnActions.filter(a => a.action !== 'end_turn');
                                                  
                                                  return (
                                                    <tr key={turn} className="border-t border-gray-800 hover:bg-gray-850">
                                                      <td className="px-3 py-2 text-center font-bold">{turn}</td>
                                                      <td className={`px-3 py-2 text-center ${isP1Turn ? 'bg-green-900/20' : ''}`}>
                                                        {formatCC(data.p1, isP1Turn)}
                                                      </td>
                                                      <td className={`px-3 py-2 text-center ${!isP1Turn ? 'bg-blue-900/20' : ''}`}>
                                                        {formatCC(data.p2, !isP1Turn)}
                                                      </td>
                                                      <td className="px-3 py-2 text-left text-xs">
                                                        {visibleActions.slice(0, 10).map((a, i) => (
                                                          <React.Fragment key={i}>
                                                            {i > 0 && <span className="text-gray-600">, </span>}
                                                            <span className={a.player === 'player1' ? 'text-green-400' : 'text-blue-400'}>
                                                              {a.description || `${a.action} ${a.card || ''}`}
                                                            </span>
                                                          </React.Fragment>
                                                        ))}
                                                        {visibleActions.length > 10 && <span className="text-gray-500"> +{visibleActions.length - 10} more</span>}
                                                      </td>
                                                    </tr>
                                                  );
                                                });
                                              })()}
                                              {/* Summary row aligned with columns */}
                                              <tr className="border-t border-gray-700 bg-gray-900/50">
                                                <td className="px-3 py-2 text-center text-xs text-gray-400">Total</td>
                                                <td className="px-3 py-2 text-center text-green-400 text-xs">
                                                  <span className="text-yellow-400">+{selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player1').reduce((sum, cc) => sum + cc.cc_gained, 0)}</span>
                                                  <span className="text-red-400 ml-1">-{selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player1').reduce((sum, cc) => sum + cc.cc_spent, 0)}</span>
                                                </td>
                                                <td className="px-3 py-2 text-center text-blue-400 text-xs">
                                                  <span className="text-yellow-400">+{selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player2').reduce((sum, cc) => sum + cc.cc_gained, 0)}</span>
                                                  <span className="text-red-400 ml-1">-{selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player2').reduce((sum, cc) => sum + cc.cc_spent, 0)}</span>
                                                </td>
                                                <td></td>
                                              </tr>
                                            </tbody>
                                          </table>
                                        </div>
                                      </div>
                                    ) : (
                                      <div className="text-gray-400">No CC tracking data available.</div>
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
              <div className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                <h2 className="text-xl font-bold" style={{ marginBottom: 'var(--spacing-component-md)' }}>
                  Past Simulations
                </h2>
                <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
                  {simulationRuns.map(run => (
                    <div
                      key={run.run_id}
                      className="bg-gray-900 rounded-lg cursor-pointer hover:bg-gray-850"
                      style={{ padding: 'var(--spacing-component-md)' }}
                      onClick={() => loadSimulationResults(run.run_id)}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-semibold">
                            Run #{run.run_id}
                            <span className={`text-xs rounded ${
                              run.status === 'completed' ? 'bg-green-600' :
                              run.status === 'running' ? 'bg-yellow-600' :
                              run.status === 'failed' ? 'bg-red-600' :
                              'bg-gray-600'
                            }`} style={{ marginLeft: 'var(--spacing-component-xs)', padding: '2px 6px' }}>
                              {run.status}
                            </span>
                          </div>
                          <div className="text-sm text-gray-400">
                            {run.config.deck_names.join(', ')} • {run.completed_games}/{run.total_games} games
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatRelativeTime(run.created_at)}
                          </div>
                        </div>
                        <div className="text-blue-400">View →</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDataViewer;

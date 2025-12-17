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
    error_message: string | null;
  }>;
  created_at: string;
  completed_at: string | null;
}

const AdminDataViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'summary' | 'ai-logs' | 'games' | 'playbacks' | 'users' | 'simulation'>('summary');
  const [selectedLog, setSelectedLog] = useState<AILog | null>(null);
  const [selectedPlayback, setSelectedPlayback] = useState<GamePlaybackDetail | null>(null);
  
  // Simulation state
  const [selectedDecks, setSelectedDecks] = useState<string[]>([]);
  const [player1Model, setPlayer1Model] = useState('gemini-2.0-flash');
  const [player2Model, setPlayer2Model] = useState('gemini-2.5-flash');
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
    queryKey: ['admin-ai-logs'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/admin/ai-logs?limit=50`);
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

  const truncate = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
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
              <p className="text-gray-400 text-sm">
                Showing {aiLogsData?.count || 0} most recent AI decision logs
              </p>
            </div>
            {aiLogsData?.logs.map((log: AILog) => (
              <div key={log.id} className="bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-component-lg)' }}>
                <div className="flex justify-between items-start" style={{ marginBottom: 'var(--spacing-component-md)' }}>
                  <div>
                    <h3 className="text-xl font-semibold">
                      AI Log #{log.id}
                      <span className="text-sm text-gray-400" style={{ marginLeft: 'var(--spacing-component-xs)' }}>
                        {log.model_name} v{log.prompts_version}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-400">
                      Game: {log.game_id.substring(0, 8)}... · Turn {log.turn_number} · {formatDate(log.created_at)}
                    </p>
                  </div>
                  <button
                    className="bg-blue-600 hover:bg-blue-700 rounded text-sm"
                    style={{ padding: '4px var(--spacing-component-sm)' }}
                    onClick={() => setSelectedLog(selectedLog?.id === log.id ? null : log)}
                  >
                    {selectedLog?.id === log.id ? 'Hide' : 'View Full'}
                  </button>
                </div>
                
                {selectedLog?.id === log.id ? (
                  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
                    <div>
                      <h4 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Prompt:</h4>
                      <pre className="bg-gray-900 rounded overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-md)' }}>
                        {log.prompt}
                      </pre>
                    </div>
                    <div>
                      <h4 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Response:</h4>
                      <pre className="bg-gray-900 rounded overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-md)' }}>
                        {log.response}
                      </pre>
                    </div>
                    {log.reasoning && (
                      <div>
                        <h4 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Reasoning:</h4>
                        <p className="text-gray-300">{log.reasoning}</p>
                      </div>
                    )}
                    {log.action_number !== null && (
                      <div>
                        <h4 className="font-semibold" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Action Chosen:</h4>
                        <p className="text-gray-300">Action #{log.action_number}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)' }}>
                    <p className="text-sm text-gray-400">
                      Prompt: {truncate(log.prompt, 200)}
                    </p>
                    <p className="text-sm text-gray-400">
                      Response: {truncate(log.response, 200)}
                    </p>
                  </div>
                )}
              </div>
            ))}
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
                <button
                  onClick={() => setSelectedPlayback(null)}
                  className="bg-blue-600 hover:bg-blue-700 text-white rounded"
                  style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
                >
                  ← Back to Playbacks List
                </button>
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
                      <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                      <option value="gemini-2.0-flash-lite">gemini-2.0-flash-lite</option>
                      <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                      <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
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
                      <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                      <option value="gemini-2.0-flash-lite">gemini-2.0-flash-lite</option>
                      <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                      <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
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
                  <div className="text-sm text-gray-400" style={{ marginTop: '4px' }}>
                    {selectedDecks.length >= 1 && (
                      <>
                        {selectedDecks.length === 1 ? '1 mirror matchup' : `${selectedDecks.length * (selectedDecks.length + 1) / 2} matchups`} × {iterationsPerMatchup} games = {' '}
                        <span className="text-white font-semibold">
                          {(selectedDecks.length === 1 ? 1 : selectedDecks.length * (selectedDecks.length + 1) / 2) * iterationsPerMatchup} total games
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Start Button */}
                <button
                  onClick={startSimulation}
                  disabled={isRunningSimulation || selectedDecks.length < 1}
                  className={`w-full rounded font-semibold ${
                    isRunningSimulation || selectedDecks.length < 1
                      ? 'bg-gray-600 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-700'
                  }`}
                  style={{ padding: 'var(--spacing-component-md)' }}
                >
                  {isRunningSimulation ? 'Starting...' : 'Start Simulation'}
                </button>

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

                  {/* Matchup Stats Table */}
                  <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                    Matchup Results
                  </h3>
                  <div className="bg-gray-900 rounded overflow-hidden" style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950">
                        <tr>
                          <th className="px-4 py-2 text-left">Matchup</th>
                          <th className="px-4 py-2 text-center">Games</th>
                          <th className="px-4 py-2 text-center text-green-400" title="Player 1 always goes first">
                            P1 Wins
                          </th>
                          <th className="px-4 py-2 text-center text-blue-400">P2 Wins</th>
                          <th className="px-4 py-2 text-center">Draws</th>
                          <th className="px-4 py-2 text-center">P1 Win %</th>
                          <th className="px-4 py-2 text-center">Avg Turns</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.values(selectedSimulation.matchup_stats).map((stats) => (
                          <tr key={`${stats.deck1_name}_vs_${stats.deck2_name}`} className="border-t border-gray-800">
                            <td className="px-4 py-2 font-semibold">
                              <span className="text-green-400">{stats.deck1_name}</span>
                              <span className="text-gray-500"> vs </span>
                              <span className="text-blue-400">{stats.deck2_name}</span>
                            </td>
                            <td className="px-4 py-2 text-center">{stats.games_played}</td>
                            <td className="px-4 py-2 text-center text-green-400">{stats.deck1_wins}</td>
                            <td className="px-4 py-2 text-center text-blue-400">{stats.deck2_wins}</td>
                            <td className="px-4 py-2 text-center text-gray-400">{stats.draws}</td>
                            <td className="px-4 py-2 text-center">
                              <span className={stats.deck1_win_rate > 0.5 ? 'text-green-400' : stats.deck1_win_rate < 0.5 ? 'text-red-400' : 'text-gray-400'}>
                                {(stats.deck1_win_rate * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-4 py-2 text-center text-orange-400">
                              {stats.avg_turns.toFixed(1)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Individual Games */}
                  <h3 className="text-lg font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                    Individual Games
                    <span className="text-sm font-normal text-gray-400 ml-2">(click to view CC tracking)</span>
                  </h3>
                  <div className="bg-gray-900 rounded overflow-hidden max-h-96 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950 sticky top-0">
                        <tr>
                          <th className="px-4 py-2 text-left">#</th>
                          <th className="px-4 py-2 text-left">Matchup</th>
                          <th className="px-4 py-2 text-center">Result</th>
                          <th className="px-4 py-2 text-center">Turns</th>
                          <th className="px-4 py-2 text-center">Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedSimulation.games.map(game => (
                          <tr 
                            key={game.game_number} 
                            className={`border-t border-gray-800 cursor-pointer hover:bg-gray-800 ${selectedGameDetail?.game_number === game.game_number ? 'bg-gray-800' : ''}`}
                            onClick={() => loadGameDetail(selectedSimulation.run_id, game.game_number)}
                          >
                            <td className="px-4 py-2">{game.game_number}</td>
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
                            <td className="px-4 py-2 text-center text-orange-400">{game.turn_count}</td>
                            <td className="px-4 py-2 text-center text-cyan-400">
                              {(game.duration_ms / 1000).toFixed(1)}s
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                  {/* CC Tracking Detail Panel */}
                  {loadingGameDetail && (
                    <div className="bg-gray-900 rounded p-4 mt-4 text-center text-gray-400">
                      Loading game details...
                    </div>
                  )}
                  
                  {selectedGameDetail && !loadingGameDetail && (
                    <div className="bg-gray-900 rounded p-4 mt-4">
                      <div className="flex justify-between items-center mb-4">
                        <h4 className="text-lg font-semibold">
                          Game #{selectedGameDetail.game_number} CC Tracking
                        </h4>
                        <button 
                          onClick={() => setSelectedGameDetail(null)}
                          className="text-gray-400 hover:text-white"
                        >
                          ✕ Close
                        </button>
                      </div>
                      
                      {selectedGameDetail.cc_tracking && selectedGameDetail.cc_tracking.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-950">
                              <tr>
                                <th className="px-3 py-2 text-center">Turn</th>
                                <th className="px-3 py-2 text-center">Player</th>
                                <th className="px-3 py-2 text-center">CC Start</th>
                                <th className="px-3 py-2 text-center">CC Gained</th>
                                <th className="px-3 py-2 text-center">CC Spent</th>
                                <th className="px-3 py-2 text-center">CC End</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedGameDetail.cc_tracking.map((cc, idx) => (
                                <tr 
                                  key={idx} 
                                  className="border-t border-gray-800"
                                  style={{ backgroundColor: cc.player_id === 'player1' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)' }}
                                >
                                  <td className="px-3 py-2 text-center">{cc.turn}</td>
                                  <td className={`px-3 py-2 text-center font-semibold ${cc.player_id === 'player1' ? 'text-green-400' : 'text-blue-400'}`}>
                                    {cc.player_id === 'player1' ? 'P1' : 'P2'}
                                  </td>
                                  <td className="px-3 py-2 text-center">{cc.cc_start}</td>
                                  <td className="px-3 py-2 text-center text-yellow-400">+{cc.cc_gained}</td>
                                  <td className="px-3 py-2 text-center text-red-400">-{cc.cc_spent}</td>
                                  <td className="px-3 py-2 text-center font-bold">{cc.cc_end}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          
                          {/* CC Summary */}
                          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                            <div className="bg-gray-950 rounded p-3">
                              <div className="text-green-400 font-semibold mb-2">Player 1 (P1) Summary</div>
                              <div>Total CC Gained: {selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player1').reduce((sum, cc) => sum + cc.cc_gained, 0)}</div>
                              <div>Total CC Spent: {selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player1').reduce((sum, cc) => sum + cc.cc_spent, 0)}</div>
                            </div>
                            <div className="bg-gray-950 rounded p-3">
                              <div className="text-blue-400 font-semibold mb-2">Player 2 (P2) Summary</div>
                              <div>Total CC Gained: {selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player2').reduce((sum, cc) => sum + cc.cc_gained, 0)}</div>
                              <div>Total CC Spent: {selectedGameDetail.cc_tracking.filter(cc => cc.player_id === 'player2').reduce((sum, cc) => sum + cc.cc_spent, 0)}</div>
                            </div>
                          </div>
                          
                          {/* Play-by-Play Actions */}
                          {selectedGameDetail.action_log && selectedGameDetail.action_log.length > 0 && (
                            <div className="mt-6">
                              <h5 className="font-semibold mb-2">Play-by-Play Actions</h5>
                              <div className="max-h-80 overflow-y-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-gray-950 sticky top-0">
                                    <tr>
                                      <th className="px-3 py-2 text-left">Turn</th>
                                      <th className="px-3 py-2 text-left">Player</th>
                                      <th className="px-3 py-2 text-left">Action</th>
                                      <th className="px-3 py-2 text-left">Card</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {selectedGameDetail.action_log.map((entry, idx) => (
                                      <tr 
                                        key={idx} 
                                        className="border-t border-gray-800"
                                        style={{ backgroundColor: entry.player === 'player1' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)' }}
                                      >
                                        <td className="px-3 py-2">{entry.turn}</td>
                                        <td className={`px-3 py-2 ${entry.player === 'player1' ? 'text-green-400' : 'text-blue-400'}`}>
                                          {entry.player === 'player1' ? 'P1' : 'P2'}
                                        </td>
                                        <td className="px-3 py-2">{entry.action}</td>
                                        <td className="px-3 py-2 text-yellow-400">{entry.card || '-'}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-gray-400">No CC tracking data available for this game.</div>
                      )}
                    </div>
                  )}
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

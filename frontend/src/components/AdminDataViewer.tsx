/**
 * Admin data viewer for GGLTCG database.
 * 
 * Simple interface to view AI logs, game playbacks, and stats.
 */

import React, { useState } from 'react';
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
  last_game_at: string | null;
  last_game_status: string | null;
}

const AdminDataViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'summary' | 'ai-logs' | 'games' | 'playbacks' | 'users'>('summary');
  const [selectedLog, setSelectedLog] = useState<AILog | null>(null);
  const [selectedPlayback, setSelectedPlayback] = useState<GamePlaybackDetail | null>(null);

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

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">GGLTCG Admin Data Viewer</h1>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-gray-400 text-xs mb-1">Total Users</h3>
              <p className="text-2xl font-bold">{summary.users.total}</p>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-gray-400 text-xs mb-1">Games</h3>
              <p className="text-2xl font-bold">{summary.games.total}</p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.games.active} active · {summary.games.completed} completed
              </p>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-gray-400 text-xs mb-1">AI Logs</h3>
              <p className="text-2xl font-bold">{summary.ai_logs.total}</p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.ai_logs.recent_1h} in last hour
              </p>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-gray-400 text-xs mb-1">Playbacks</h3>
              <p className="text-2xl font-bold">{summary.playbacks.total}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-4 mb-6 border-b border-gray-700">
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
        </div>

        {/* Content */}
        {activeTab === 'summary' && (
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Database Overview</h2>
            <p className="text-gray-400 mb-4">
              Use the tabs above to view AI decision logs, game data, and playback recordings.
            </p>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Recent Activity (Last 24h)</h3>
                <p className="text-gray-400">{summary?.games.recent_24h || 0} games started</p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">AI Activity (Last Hour)</h3>
                <p className="text-gray-400">{summary?.ai_logs.recent_1h || 0} AI decisions logged</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai-logs' && (
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg mb-4">
              <p className="text-gray-400 text-sm">
                Showing {aiLogsData?.count || 0} most recent AI decision logs
              </p>
            </div>
            {aiLogsData?.logs.map((log: AILog) => (
              <div key={log.id} className="bg-gray-800 p-6 rounded-lg">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-semibold">
                      AI Log #{log.id}
                      <span className="ml-2 text-sm text-gray-400">
                        {log.model_name} v{log.prompts_version}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-400">
                      Game: {log.game_id.substring(0, 8)}... · Turn {log.turn_number} · {formatDate(log.created_at)}
                    </p>
                  </div>
                  <button
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
                    onClick={() => setSelectedLog(selectedLog?.id === log.id ? null : log)}
                  >
                    {selectedLog?.id === log.id ? 'Hide' : 'View Full'}
                  </button>
                </div>
                
                {selectedLog?.id === log.id ? (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold mb-2">Prompt:</h4>
                      <pre className="bg-gray-900 p-4 rounded overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap">
                        {log.prompt}
                      </pre>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">Response:</h4>
                      <pre className="bg-gray-900 p-4 rounded overflow-x-auto text-sm text-gray-300 whitespace-pre-wrap">
                        {log.response}
                      </pre>
                    </div>
                    {log.reasoning && (
                      <div>
                        <h4 className="font-semibold mb-2">Reasoning:</h4>
                        <p className="text-gray-300">{log.reasoning}</p>
                      </div>
                    )}
                    {log.action_number !== null && (
                      <div>
                        <h4 className="font-semibold mb-2">Action Chosen:</h4>
                        <p className="text-gray-300">Action #{log.action_number}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
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
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg mb-4">
              <p className="text-gray-400 text-sm">
                Showing {gamesData?.count || 0} most recent games
              </p>
            </div>
            {gamesData?.games.map((game: Game) => (
              <div key={game.id} className="bg-gray-800 p-6 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-xl font-semibold">
                      {game.player1_name} vs {game.player2_name}
                      <span className={`ml-3 px-2 py-1 text-xs rounded ${
                        game.status === 'active' ? 'bg-green-600' :
                        game.status === 'completed' ? 'bg-blue-600' :
                        'bg-gray-600'
                      }`}>
                        {game.status}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-400 mt-1 font-mono">
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
                      <p className="text-sm text-green-400 mt-2">
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
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg mb-4">
              <p className="text-gray-400 text-sm">
                Showing {playbacksData?.count || 0} most recent completed games
              </p>
            </div>
            {selectedPlayback ? (
              <div className="space-y-4">
                <button
                  onClick={() => setSelectedPlayback(null)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  ← Back to Playbacks List
                </button>
                <div className="bg-gray-800 p-6 rounded-lg">
                  {/* Header - Player vs Player */}
                  <h2 className="text-2xl font-bold mb-4">
                    {selectedPlayback.player1_name} vs {selectedPlayback.player2_name}
                  </h2>

                  {/* Winner and Game Stats - Prominent */}
                  <div className="mb-2">
                    <span className="text-xl font-bold">Game winner: </span>
                    <span className="text-xl font-bold text-green-400">
                      {selectedPlayback.winner_id === selectedPlayback.player1_id
                        ? selectedPlayback.player1_name
                        : selectedPlayback.player2_name}
                    </span>
                    <span className="text-xl">, in {selectedPlayback.turn_count} turns, {formatDuration(selectedPlayback.created_at, selectedPlayback.completed_at)}.</span>
                  </div>
                  
                  {/* Game ID and Timestamp - Discrete */}
                  <div className="text-sm text-gray-500 mb-8">
                    (Game ID: {selectedPlayback.game_id}, Completed: {formatDate(selectedPlayback.completed_at || '')})
                  </div>

                  {/* Starting Decks - Table Format */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-2">Starting Decks</h3>
                    <div className="bg-gray-900 rounded overflow-hidden">
                      <table className="w-full text-sm">
                        <tbody>
                          <tr className="border-b border-gray-700">
                            <td className="px-4 py-3 font-semibold bg-gray-950 whitespace-nowrap">
                              {selectedPlayback.player1_name}
                              {selectedPlayback.first_player_id === selectedPlayback.player1_id && (
                                <span className="text-xs text-yellow-400 ml-2">(**first**)</span>
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
                                <span className="text-xs text-yellow-400 ml-2">(**first**)</span>
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
                    <h3 className="text-lg font-semibold mb-3">Play-by-Play</h3>
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
                <div key={playback.id} className="bg-gray-800 p-6 rounded-lg">
                  <h3 className="text-xl font-semibold">
                    {playback.player1_name} vs {playback.player2_name}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1 font-mono">
                    Game ID: {playback.game_id}
                  </p>
                  <p className="text-sm text-gray-400">
                    {playback.turn_count} turns · {formatDuration(playback.created_at, playback.completed_at)}
                  </p>
                  {playback.winner_id && (
                    <p className="text-sm text-green-400 mt-2">
                      Winner: {playback.winner_id === playback.player1_id ? playback.player1_name : playback.player2_name}
                    </p>
                  )}
                  <p className="text-sm text-gray-400 mt-2">
                    Completed: {playback.completed_at ? formatDate(playback.completed_at) : 'In progress'}
                  </p>
                  <button
                    onClick={() => loadPlaybackDetails(playback.game_id)}
                    className="inline-block mt-3 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
                  >
                    View Playback Details
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg mb-4">
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
      </div>
    </div>
  );
};

export default AdminDataViewer;

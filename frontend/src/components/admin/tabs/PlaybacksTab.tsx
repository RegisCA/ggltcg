/**
 * Playbacks tab — completed-game recordings with metrics, deck tables,
 * turn-by-turn charge summary, and play-by-play. JSX moved verbatim from
 * AdminDataViewer.tsx; owns its own selected-playback state.
 */

import React, { useState } from 'react';
import type { AdminPlaybacksResponse } from '../../../api/adminService';
import { getPlaybackDetail } from '../../../api/adminService';
import { usePlaybackAiLogs } from '../../../hooks/useAdminData';
import type { GamePlayback, GamePlaybackDetail, TurnCharge } from '../types';
import {
  groupLogsByTurn,
  formatDate,
  formatDuration,
  countSymptoms,
  mergeCounts,
  totalCount,
  formatCountsInline,
  buildTurnTextForSymptoms,
  buildLogTextForSymptoms,
  computeActiveTurnChargeAveragesFromPlayback,
} from '../utils';
import DataTable, { type DataTableColumn } from '../shared/DataTable';

interface PlaybacksTabProps {
  playbacksData: AdminPlaybacksResponse | undefined;
  onNavigateToAiLogs: (gameId: string) => void;
}

const PlaybacksTab: React.FC<PlaybacksTabProps> = ({ playbacksData, onNavigateToAiLogs }) => {
  const [selectedPlayback, setSelectedPlayback] = useState<GamePlaybackDetail | null>(null);

  // Fetch AI logs for the selected playback (for metrics/symptoms)
  const { data: playbackAiLogsData } = usePlaybackAiLogs(selectedPlayback?.game_id);

  const loadPlaybackDetails = async (gameId: string) => {
    try {
      const detail = await getPlaybackDetail(gameId);
      setSelectedPlayback(detail);
    } catch (error) {
      console.error('Failed to load playback details:', error);
      alert('Failed to load playback details');
    }
  };

  return (
    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
      <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
        <p className="text-[var(--ink-faint)] text-sm">
          Showing {playbacksData?.count || 0} most recent completed games
        </p>
      </div>
      {selectedPlayback ? (
        <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
          <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
            <button
              onClick={() => setSelectedPlayback(null)}
              className="bg-blue-600 hover:bg-blue-700 text-[var(--ink-text)] rounded"
              style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
            >
              ← Back to Playbacks List
            </button>
            <button
              onClick={() => onNavigateToAiLogs(selectedPlayback.game_id)}
              className="bg-purple-600 hover:bg-purple-700 text-[var(--ink-text)] rounded"
              style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-md)' }}
            >
              View AI Logs for this Game →
            </button>
          </div>
          <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-lg)' }}>
            {/* Header - Player vs Player */}
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-md)' }}>
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
            <div className="text-sm text-[var(--ink-faint)]" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
              (Game ID: {selectedPlayback.game_id}, Completed: {formatDate(selectedPlayback.completed_at || '')})
            </div>

            {/* Debug Metrics */}
            {(() => {
              const chargeAverages = computeActiveTurnChargeAveragesFromPlayback(
                selectedPlayback.charge_tracking,
                selectedPlayback.player1_id,
                selectedPlayback.player2_id
              );

              // Symptom totals and per-turn symptom counts (from AI logs)
              const items = playbackAiLogsData?.logs ? groupLogsByTurn(playbackAiLogsData.logs) : [];
              const byTurn = new Map<number, Record<string, number>>();
              let totals: Record<string, number> = {};
              for (const it of items) {
                if ('logs' in it) {
                  const tg = it;
                  const counts = countSymptoms(buildTurnTextForSymptoms(tg));
                  byTurn.set(tg.turn_number, counts);
                  totals = mergeCounts(totals, counts);
                } else {
                  const lg = it;
                  const counts = countSymptoms(buildLogTextForSymptoms(lg));
                  byTurn.set(lg.turn_number, mergeCounts(byTurn.get(lg.turn_number) || {}, counts));
                  totals = mergeCounts(totals, counts);
                }
              }
              const turnsWithSymptoms = Array.from(byTurn.entries())
                .map(([turn, counts]) => ({ turn, total: totalCount(counts), counts }))
                .filter(x => x.total > 0)
                .sort((a, b) => a.turn - b.turn);

              return (
                <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                  <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-xs)' }}>Metrics</h3>
                  <div className="bg-black/20 rounded" style={{ padding: 'var(--spacing-component-md)' }}>
                    <div className="text-sm text-[var(--ink-muted)]" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                      <span className="text-[var(--ink-faint)]">Avg Charge end (active turns): </span>
                      <span className="text-green-400">{selectedPlayback.player1_name}</span>
                      <span className="text-[var(--ink-muted)]"> {chargeAverages.p1_avg !== null ? chargeAverages.p1_avg.toFixed(2) : '—'} </span>
                      <span className="text-[var(--ink-faint)]">({chargeAverages.p1_samples} turns)</span>
                      <span className="text-[var(--ink-faint)]"> · </span>
                      <span className="text-blue-400">{selectedPlayback.player2_name}</span>
                      <span className="text-[var(--ink-muted)]"> {chargeAverages.p2_avg !== null ? chargeAverages.p2_avg.toFixed(2) : '—'} </span>
                      <span className="text-[var(--ink-faint)]">({chargeAverages.p2_samples} turns)</span>
                    </div>

                    <div className="text-sm text-[var(--ink-muted)]">
                      <span className="text-[var(--ink-faint)]">Symptoms (game): </span>
                      <span>{formatCountsInline(totals)}</span>
                      <span className="text-[var(--ink-faint)]"> · total {totalCount(totals)}</span>
                    </div>

                    {turnsWithSymptoms.length > 0 && (
                      <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                        <summary className="text-[var(--ink-faint)] cursor-pointer hover:text-[var(--ink-muted)]">
                          View symptoms by turn ({turnsWithSymptoms.length} turns)
                        </summary>
                        <div className="text-xs text-[var(--ink-faint)]" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                          {turnsWithSymptoms.map(x => (
                            <div key={x.turn}>
                              Turn {x.turn}: {formatCountsInline(x.counts)} (total {x.total})
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Starting Decks - Table Format */}
            <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
              <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-xs)' }}>Starting Decks</h3>
              <div className="bg-black/20 rounded overflow-hidden">
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-white/10">
                      <td className="px-4 py-3 font-semibold bg-black/30 whitespace-nowrap">
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
                      <td className="px-4 py-3 font-semibold bg-black/30 whitespace-nowrap">
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

            {/* Charge Tracking with Actions - Compact timeline view like Simulation */}
            {selectedPlayback.charge_tracking && selectedPlayback.charge_tracking.length > 0 && (
              <div style={{ marginBottom: 'var(--spacing-component-lg)' }}>
                <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-sm)' }}>Turn-by-Turn Summary</h3>
                <div className="bg-black/20 rounded overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead className="bg-black/30">
                      <tr>
                        <th className="px-3 py-2 text-center border-b border-white/10 w-16">Turn</th>
                        <th className="px-3 py-2 text-center text-green-400 border-b border-white/10 w-24">
                          {selectedPlayback.player1_name.length > 8 ? 'P1' : selectedPlayback.player1_name} Charge
                        </th>
                        <th className="px-3 py-2 text-center text-blue-400 border-b border-white/10 w-24">
                          {selectedPlayback.player2_name.length > 8 ? 'P2' : selectedPlayback.player2_name} Charge
                        </th>
                        <th className="px-3 py-2 text-left border-b border-white/10">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        // Group Charge tracking by turn, using actual player IDs
                        const p1Id = selectedPlayback.player1_id;
                        const p2Id = selectedPlayback.player2_id;
                        const turnMap = new Map<number, { p1?: TurnCharge, p2?: TurnCharge }>();
                        selectedPlayback.charge_tracking!.forEach(charge => {
                          if (!turnMap.has(charge.turn)) turnMap.set(charge.turn, {});
                          const entry = turnMap.get(charge.turn)!;
                          if (charge.player_id === p1Id) entry.p1 = charge;
                          else if (charge.player_id === p2Id) entry.p2 = charge;
                        });
                        // Include turns from play_by_play even if not in charge_tracking (e.g., final turn)
                        const allTurns = new Set<number>(turnMap.keys());
                        selectedPlayback.play_by_play?.forEach(action => allTurns.add(action.turn));
                        const turns = Array.from(allTurns).sort((a, b) => a - b);

                        // Group play-by-play actions by turn
                        const actionsByTurn = new Map<number, typeof selectedPlayback.play_by_play>();
                        selectedPlayback.play_by_play?.forEach(action => {
                          if (!actionsByTurn.has(action.turn)) actionsByTurn.set(action.turn, []);
                          actionsByTurn.get(action.turn)!.push(action);
                        });

                        // Format Charge: simple start-spent→end format
                        const formatCharge = (data: TurnCharge | undefined, isActive: boolean): React.ReactNode => {
                          if (!data) return <span className="text-[var(--ink-faint)]">—</span>;
                          return (
                            <span className={`font-mono ${isActive ? '' : 'opacity-60'}`}>
                              {data.charge_start}
                              {data.charge_gained > 0 && <span className="text-yellow-400">+{data.charge_gained}</span>}
                              {data.charge_spent > 0 && <span className="text-red-400">-{data.charge_spent}</span>}
                              <span className="text-[var(--ink-faint)]">→</span>
                              <span className="font-bold">{data.charge_end}</span>
                            </span>
                          );
                        };

                        return turns.map(turn => {
                          const data = turnMap.get(turn) || { p1: undefined, p2: undefined };
                          const turnActions = actionsByTurn.get(turn) || [];
                          const isP1Turn = turn % 2 === 1;

                          // Filter out end_turn actions for cleaner display
                          const visibleActions = turnActions.filter(a => a.action_type !== 'end_turn');

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
                                {visibleActions.slice(0, 8).map((a, i) => (
                                  <React.Fragment key={i}>
                                    {i > 0 && <span className="text-[var(--ink-faint)]">, </span>}
                                    <span className={a.player === selectedPlayback.player1_name ? 'text-green-400' : 'text-blue-400'}>
                                      {a.description}
                                    </span>
                                  </React.Fragment>
                                ))}
                                {visibleActions.length > 8 && <span className="text-[var(--ink-faint)]"> +{visibleActions.length - 8} more</span>}
                              </td>
                            </tr>
                          );
                        });
                      })()}
                      {/* Summary row */}
                      {(() => {
                        const p1Id = selectedPlayback.player1_id;
                        const p2Id = selectedPlayback.player2_id;
                        const p1Gained = selectedPlayback.charge_tracking!.filter(charge => charge.player_id === p1Id).reduce((sum, charge) => sum + charge.charge_gained, 0);
                        const p1Spent = selectedPlayback.charge_tracking!.filter(charge => charge.player_id === p1Id).reduce((sum, charge) => sum + charge.charge_spent, 0);
                        const p2Gained = selectedPlayback.charge_tracking!.filter(charge => charge.player_id === p2Id).reduce((sum, charge) => sum + charge.charge_gained, 0);
                        const p2Spent = selectedPlayback.charge_tracking!.filter(charge => charge.player_id === p2Id).reduce((sum, charge) => sum + charge.charge_spent, 0);
                        return (
                          <tr className="border-t border-white/10 bg-black/20/50">
                            <td className="px-3 py-2 text-center text-xs text-[var(--ink-faint)]">Total</td>
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
              <h3 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-card-name)', marginBottom: 'var(--spacing-component-sm)' }}>Play-by-Play</h3>
              <div className="bg-black/20 rounded overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-black/30">
                    <tr>
                      <th className="px-4 py-2 text-left">Turn</th>
                      <th className="px-4 py-2 text-left">Player</th>
                      <th className="px-4 py-2 text-left">Action</th>
                      <th className="px-4 py-2 text-left">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedPlayback.play_by_play.map((entry, index) => (
                      <tr key={index} className="border-t border-white/10">
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
        (() => {
          const columns: DataTableColumn<GamePlayback>[] = [
            {
              key: 'players',
              header: 'Players',
              render: (playback) => (
                <div>
                  <span className="font-semibold">{playback.player1_name} vs {playback.player2_name}</span>
                  {playback.winner_id && (
                    <div className="text-xs text-green-400">
                      Winner: {playback.winner_id === playback.player1_id ? playback.player1_name : playback.player2_name}
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'game_id',
              header: 'Game ID',
              render: (playback) => <span className="text-xs font-mono text-[var(--ink-faint)]">{playback.game_id}</span>,
            },
            {
              key: 'duration',
              header: 'Turns / Duration',
              render: (playback) => (
                <span className="text-[var(--ink-faint)] text-xs">
                  {playback.turn_count} turns · {formatDuration(playback.created_at, playback.completed_at)}
                </span>
              ),
            },
            {
              key: 'completed',
              header: 'Completed',
              render: (playback) => (
                <span className="text-[var(--ink-faint)] text-xs">
                  {playback.completed_at ? formatDate(playback.completed_at) : 'In progress'}
                </span>
              ),
            },
            {
              key: 'actions',
              header: '',
              render: (playback) => (
                <button
                  onClick={() => loadPlaybackDetails(playback.game_id)}
                  className="inline-block bg-blue-600 hover:bg-blue-700 rounded text-xs"
                  style={{ padding: '4px var(--spacing-component-sm)' }}
                >
                  View Playback Details
                </button>
              ),
            },
          ];
          return (
            <DataTable
              columns={columns}
              rows={playbacksData?.games || []}
              rowKey={(playback) => playback.id}
              emptyMessage="No playbacks to display."
            />
          );
        })()
      )}
    </div>
  );
};

export default PlaybacksTab;

/**
 * AI Logs tab — planner turn groups and legacy per-action logs.
 * JSX moved verbatim from AdminDataViewer.tsx; owns its own selected-log
 * and expanded-turn state.
 */

import React, { useMemo, useState } from 'react';
import { plannerModeLabel } from '../../../utils/plannerMode';
import type { AiLogsResponse } from '../../../api/adminService';
import type { AILog } from '../types';
import {
  groupLogsByTurn,
  formatDate,
  formatRelativeTime,
  countSymptoms,
  totalCount,
  formatCountsInline,
  buildTurnTextForSymptoms,
  buildTurnCopyBundle,
  copyTextToClipboard,
  normalizeText,
} from '../utils';

interface AiLogsTabProps {
  aiLogsData: AiLogsResponse | undefined;
  gameIdFilter: string | null;
  onClearFilter: () => void;
}

const ALL_PLAYERS = '__all_players__';
const ALL_DECISION_TYPES = '__all_decision_types__';

const decisionTypeOf = (item: ReturnType<typeof groupLogsByTurn>[number]): string =>
  'logs' in item ? plannerModeLabel(item.planner, item.ai_version) : 'v2 (legacy)';

const AiLogsTab: React.FC<AiLogsTabProps> = ({ aiLogsData, gameIdFilter, onClearFilter }) => {
  const [selectedLog, setSelectedLog] = useState<AILog | null>(null);
  const [expandedTurns, setExpandedTurns] = useState<Set<string>>(new Set());
  const [playerFilter, setPlayerFilter] = useState<string>(ALL_PLAYERS);
  const [decisionTypeFilter, setDecisionTypeFilter] = useState<string>(ALL_DECISION_TYPES);

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

  const allItems = useMemo(
    () => (aiLogsData?.logs ? groupLogsByTurn(aiLogsData.logs) : []),
    [aiLogsData]
  );

  const playerOptions = useMemo(
    () => Array.from(new Set(allItems.map(item => item.player_id))).sort(),
    [allItems]
  );
  const decisionTypeOptions = useMemo(
    () => Array.from(new Set(allItems.map(decisionTypeOf))).sort(),
    [allItems]
  );

  const items = useMemo(
    () =>
      allItems.filter(item => {
        if (playerFilter !== ALL_PLAYERS && item.player_id !== playerFilter) return false;
        if (decisionTypeFilter !== ALL_DECISION_TYPES && decisionTypeOf(item) !== decisionTypeFilter) return false;
        return true;
      }),
    [allItems, playerFilter, decisionTypeFilter]
  );

  const expandAll = () => {
    const keys: string[] = [];
    for (const item of items) {
      if ('logs' in item) keys.push(item.key);
    }
    setExpandedTurns(new Set(keys));
  };

  const collapseAll = () => setExpandedTurns(new Set());

  return (
    <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
      <div className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-md)' }}>
        {gameIdFilter ? (
          <div className="flex justify-between items-center">
            <p className="text-sm">
              <span className="text-purple-400 font-semibold">Filtered by Game: </span>
              <span className="text-[var(--ink-muted)] font-mono">{gameIdFilter}</span>
              <span className="text-[var(--ink-faint)]"> ({aiLogsData?.count || 0} logs)</span>
            </p>
            <button
              onClick={onClearFilter}
              className="bg-white/10 hover:bg-white/15 text-[var(--ink-text)] rounded text-sm"
              style={{ padding: '4px var(--spacing-component-sm)' }}
            >
              Clear Filter
            </button>
          </div>
        ) : (
          <p className="text-[var(--ink-faint)] text-sm">
            Showing {aiLogsData?.count || 0} most recent AI decisions (planner turns grouped)
          </p>
        )}
      </div>

      {/* Filters + expand/collapse controls */}
      <div className="flex flex-wrap items-center bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)', gap: 'var(--spacing-component-md)' }}>
        <label className="flex items-center text-sm" style={{ gap: 'var(--spacing-component-xs)' }}>
          <span className="text-[var(--ink-faint)]">Player:</span>
          <select
            value={playerFilter}
            onChange={(e) => setPlayerFilter(e.target.value)}
            className="bg-black/20 border border-white/10 rounded text-sm text-[var(--ink-text)]"
            style={{ padding: '4px var(--spacing-component-sm)' }}
          >
            <option value={ALL_PLAYERS}>All players</option>
            {playerOptions.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center text-sm" style={{ gap: 'var(--spacing-component-xs)' }}>
          <span className="text-[var(--ink-faint)]">Decision type:</span>
          <select
            value={decisionTypeFilter}
            onChange={(e) => setDecisionTypeFilter(e.target.value)}
            className="bg-black/20 border border-white/10 rounded text-sm text-[var(--ink-text)]"
            style={{ padding: '4px var(--spacing-component-sm)' }}
          >
            <option value={ALL_DECISION_TYPES}>All decision types</option>
            {decisionTypeOptions.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>
        <div className="flex" style={{ gap: 'var(--spacing-component-xs)', marginLeft: 'auto' }}>
          <button
            onClick={expandAll}
            className="bg-white/10 hover:bg-white/15 text-[var(--ink-text)] rounded text-xs"
            style={{ padding: '4px var(--spacing-component-sm)' }}
          >
            Expand all
          </button>
          <button
            onClick={collapseAll}
            className="bg-white/10 hover:bg-white/15 text-[var(--ink-text)] rounded text-xs"
            style={{ padding: '4px var(--spacing-component-sm)' }}
          >
            Collapse all
          </button>
        </div>
      </div>

      {items.map((item) => {
        // Turn Group (has a turn_plan)
        if ('logs' in item) {
          const turnGroup = item;
          const isExpanded = expandedTurns.has(turnGroup.key);
          const completedActions = turnGroup.logs.length;
          const totalActions = turnGroup.turn_plan?.total_actions || completedActions;
          const planCompleted = completedActions === totalActions && !turnGroup.has_fallback;
          const turnSymptomCounts = countSymptoms(buildTurnTextForSymptoms(turnGroup));
          const enumDebug = turnGroup.turn_plan?.enum_debug as Record<string, unknown> | undefined;
          const hasSelectionArtifacts =
            !!turnGroup.turn_plan?.selection_prompt || !!turnGroup.turn_plan?.selection_response;

          const planningPromptText = turnGroup.turn_plan?.planning_prompt as string | undefined;
          const planningResponseText = turnGroup.turn_plan?.planning_response as string | undefined;

          return (
            <div key={turnGroup.key} className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
              {/* Compact Turn Header */}
              <div
                className="flex justify-between items-center cursor-pointer"
                onClick={() => toggleTurnExpanded(turnGroup.key)}
              >
                <div className="flex items-center flex-wrap" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <span className="text-xs rounded bg-purple-600" style={{ padding: '2px var(--spacing-component-xs)' }} title="Planner">{plannerModeLabel(turnGroup.planner, turnGroup.ai_version)}</span>
                  <span className="font-semibold">Turn {turnGroup.turn_number}</span>
                  <span className="text-[var(--ink-faint)] text-sm">Game: {turnGroup.game_id.substring(0, 8)}...</span>
                  <span className="text-[var(--ink-faint)] text-sm">{turnGroup.model_name}</span>
                  <span className="text-[var(--ink-faint)] text-xs" title={formatDate(turnGroup.created_at)}>
                    {formatRelativeTime(turnGroup.created_at)}
                  </span>
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
                <span className="text-[var(--ink-faint)]">{isExpanded ? '▼' : '▶'}</span>
              </div>

              {/* Expanded Turn Details */}
              {isExpanded && turnGroup.turn_plan && (
                <div style={{ marginTop: 'var(--spacing-component-md)' }}>
                  <div className="flex justify-end" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                    <button
                      className="bg-white/10 hover:bg-white/15 text-[var(--ink-text)] rounded text-xs"
                      style={{ padding: '4px var(--spacing-component-sm)' }}
                      onClick={async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const ok = await copyTextToClipboard(buildTurnCopyBundle(turnGroup));
                        if (!ok) alert('Copy failed (clipboard unavailable).');
                      }}
                      title="Copy all prompts/responses/diagnostics for this turn"
                    >
                      Copy turn logs
                    </button>
                  </div>

                  {/* Symptoms (turn) */}
                  <div className="bg-black/20 rounded text-sm" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                    <span className="text-[var(--ink-faint)]">Symptoms (turn): </span>
                    <span className="text-[var(--ink-muted)]">{formatCountsInline(turnSymptomCounts)}</span>
                    <span className="text-[var(--ink-faint)]"> · total {totalCount(turnSymptomCounts)}</span>
                  </div>

                  {/* Strategy */}
                  <div className="bg-black/20 rounded" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                    <span className="text-purple-400 font-semibold">Strategy: </span>
                    <span className="text-[var(--ink-muted)]">{turnGroup.turn_plan.strategy}</span>
                  </div>

                  {/* Turn Metrics */}
                  <div className="flex flex-wrap text-sm" style={{ gap: 'var(--spacing-component-md)', marginBottom: 'var(--spacing-component-sm)' }}>
                    <span><span className="text-[var(--ink-faint)]">Charge:</span> {turnGroup.turn_plan.charge_start} → {turnGroup.turn_plan.charge_after_plan}</span>
                    <span><span className="text-[var(--ink-faint)]">Target:</span> Break {turnGroup.turn_plan.expected_cards_broken} cards</span>
                  </div>

                  {/* Enumerator/selection diagnostics (if available) */}
                  {!!enumDebug && (
                    <div className="bg-black/20 rounded text-sm" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                      <span className="text-[var(--ink-faint)]">Planner diagnostics: </span>
                      <span className="text-[var(--ink-muted)]">
                        sequences generated: {(enumDebug?.sequences_generated as number | undefined) ?? 'N/A'}
                        {' · '}selection index: {(enumDebug?.selection_index_used as number | undefined) ?? 'N/A'}
                        {' · '}parse_error: {String((enumDebug?.selection_parse_error as boolean | undefined) ?? false)}
                        {' · '}invalid_index: {String((enumDebug?.selection_invalid_index as boolean | undefined) ?? false)}
                        {' · '}fallback_used: {String((enumDebug?.selection_fallback_used as boolean | undefined) ?? false)}
                      </span>
                      {!!enumDebug?.enumeration_exception && (
                        <div className="text-red-300 text-xs" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                          ❌ Enumeration failed (0 sequences, fell back to plain end_turn): {String(enumDebug.enumeration_exception)}
                        </div>
                      )}
                      {!!enumDebug?.selection_exception && (
                        <div className="text-red-300 text-xs" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                          ❌ Strategic selection failed: {String(enumDebug.selection_exception)}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Fallback Warning */}
                  {turnGroup.has_fallback && turnGroup.fallback_reason && (
                    <div className="bg-yellow-900/30 border border-yellow-600 rounded text-sm" style={{ padding: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-sm)' }}>
                      <span className="text-yellow-400 font-semibold">⚠️ Fallback: </span>
                      <span className="text-yellow-200">{turnGroup.fallback_reason}</span>
                    </div>
                  )}

                  {/* Planned Action Sequence (from first log with action_sequence) */}
                  {!!turnGroup.turn_plan.action_sequence && turnGroup.turn_plan.action_sequence.length > 0 && (
                    <div className="text-sm" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                      <span className="text-[var(--ink-faint)]">Planned actions:</span>
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
                            <li key={idx} className={notAttempted ? "text-[var(--ink-faint)]" : "text-[var(--ink-muted)]"}>
                              {/* Execution status indicator */}
                              {isSuccess && <span className="text-green-400">✅ </span>}
                              {isMatchedButNotExecuted && <span className="text-yellow-600">⚠️ </span>}
                              {(isExecutionFailed || isMatchFailed) && <span className="text-red-400">❌ </span>}
                              {isLLMFallback && <span className="text-yellow-400">⚠️ </span>}
                              {notAttempted && <span className="text-[var(--ink-faint)]">⊘ </span>}

                              <span className="text-blue-400">{action.action_type}</span>
                              {action.card_name && <span> {action.card_name}</span>}
                              {action.target_names && action.target_names.length > 0 && (
                                <span className="text-[var(--ink-faint)]"> → {action.target_names.join(', ')}</span>
                              )}
                              <span className="text-[var(--ink-faint)]"> ({action.charge_cost} Charge)</span>

                              {/* Matched but not executed */}
                              {isMatchedButNotExecuted && (
                                <span className="text-yellow-600 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                  ⚠️ Matched to available action but execution not confirmed
                                </span>
                              )}

                              {/* Not attempted indicator */}
                              {notAttempted && (
                                <span className="text-[var(--ink-faint)] text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                  Plan execution stopped before this action
                                </span>
                              )}

                              {/* Execution failure reason - show for any failure */}
                              {execLog?.reason && (isExecutionFailed || isMatchFailed) && (
                                <span className="text-red-300 text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
                                  ❌ {isExecutionFailed ? 'Execution failed: ' : 'Match failed: '}{execLog.reason}
                                </span>
                              )}

                              {/* Enum sequences carry one reasoning for the whole
                                  plan (shown in "Strategy:" above), not per action —
                                  action.reasoning is always the literal sentinel
                                  below, so skip rendering it. */}
                              {action.reasoning && action.reasoning !== 'No reasoning provided' && !notAttempted && (
                                <span className="text-[var(--ink-faint)] text-xs block" style={{ marginLeft: 'var(--spacing-component-lg)' }}>
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
                  {typeof planningPromptText === 'string' && (
                    <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                      <summary className="text-[var(--ink-faint)] cursor-pointer hover:text-[var(--ink-muted)]">
                        View planning prompt ({planningPromptText.length} chars)
                      </summary>
                      <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-faint)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                        {planningPromptText}
                      </pre>
                    </details>
                  )}

                  {/* Planning Response (TurnPlan JSON - collapsible) */}
                  {typeof planningResponseText === 'string' && (
                    <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                      <summary className="text-[var(--ink-faint)] cursor-pointer hover:text-[var(--ink-muted)]">
                        View planning response ({planningResponseText.length} chars)
                      </summary>
                      <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-faint)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                        {planningResponseText}
                      </pre>
                    </details>
                  )}

                  {/* Executed actions (from logs - fallback if no action_sequence) */}
                  {(!turnGroup.turn_plan.action_sequence || turnGroup.turn_plan.action_sequence.length === 0) && (
                    <div className="text-sm">
                      <span className="text-[var(--ink-faint)]">Actions executed:</span>
                      <ol className="list-decimal list-inside" style={{ marginTop: 'var(--spacing-component-xs)' }}>
                        {turnGroup.logs
                          .sort((a, b) => (a.turn_plan?.current_action || 0) - (b.turn_plan?.current_action || 0))
                          .map((log) => (
                            <li key={log.id} className="text-[var(--ink-muted)]">
                              {log.reasoning || `Action #${log.turn_plan?.current_action || '?'}`}
                              {log.plan_execution_status === 'fallback' && (
                                <span className="text-yellow-400 text-xs" style={{ marginLeft: 'var(--spacing-component-xs)' }}>(fallback)</span>
                              )}
                            </li>
                          ))}
                      </ol>
                    </div>
                  )}

                  {/* Strategic selection prompt/response (collapsible) — only
                      shown when distinct from the planning prompt/response
                      above (it always is the same call for enum, since there's
                      no separate sequence-generation LLM request). */}
                  {hasSelectionArtifacts && turnGroup.turn_plan.selection_prompt && normalizeText(turnGroup.turn_plan.selection_prompt) !== normalizeText(turnGroup.turn_plan.planning_prompt) && (
                    <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                      <summary className="text-[var(--ink-faint)] cursor-pointer hover:text-[var(--ink-muted)]">
                        View strategic selection prompt ({turnGroup.turn_plan.selection_prompt.length} chars)
                      </summary>
                      <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-faint)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                        {turnGroup.turn_plan.selection_prompt}
                      </pre>
                    </details>
                  )}
                  {hasSelectionArtifacts && turnGroup.turn_plan.selection_response && normalizeText(turnGroup.turn_plan.selection_response) !== normalizeText(turnGroup.turn_plan.planning_response) && (
                    <details className="text-sm" style={{ marginTop: 'var(--spacing-component-sm)' }}>
                      <summary className="text-[var(--ink-faint)] cursor-pointer hover:text-[var(--ink-muted)]">
                        View strategic selection response ({turnGroup.turn_plan.selection_response.length} chars)
                      </summary>
                      <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-faint)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)', maxHeight: '300px', overflow: 'auto' }}>
                        {turnGroup.turn_plan.selection_response}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          );
        }

        // V2 Individual Log (unchanged display)
        const log = item;
        return (
          <div key={log.id} className="bg-panel rounded-lg border border-white/10" style={{ padding: 'var(--spacing-component-md)' }}>
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center flex-wrap" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <span className="text-xs rounded bg-white/10" style={{ padding: '2px var(--spacing-component-xs)' }}>v2</span>
                  <span className="font-semibold">Turn {log.turn_number}</span>
                  <span className="text-[var(--ink-faint)] text-sm">Game: {log.game_id.substring(0, 8)}...</span>
                  <span className="text-[var(--ink-faint)] text-sm">{log.model_name}</span>
                </div>
                <p className="text-sm text-[var(--ink-faint)]" style={{ marginTop: 'var(--spacing-component-xs)' }} title={formatDate(log.created_at)}>
                  {formatRelativeTime(log.created_at)}
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
                    <span className="text-[var(--ink-faint)] text-sm">Reasoning: </span>
                    <span className="text-[var(--ink-muted)] text-sm">{log.reasoning}</span>
                  </div>
                )}
                {log.prompt && (
                  <div>
                    <h4 className="font-semibold text-sm" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Prompt:</h4>
                    <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-muted)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)', maxHeight: '200px', overflow: 'auto' }}>
                      {log.prompt}
                    </pre>
                  </div>
                )}
                {log.response && (
                  <div>
                    <h4 className="font-semibold text-sm" style={{ marginBottom: 'var(--spacing-component-xs)' }}>Response:</h4>
                    <pre className="bg-black/20 rounded overflow-x-auto text-xs text-[var(--ink-muted)] whitespace-pre-wrap" style={{ padding: 'var(--spacing-component-sm)' }}>
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
  );
};

export default AiLogsTab;

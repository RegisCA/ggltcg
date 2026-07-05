/**
 * Victory Screen — restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md §8).
 *
 * No mockup exists for this screen (6a/6b/3c only cover the board + target
 * modal) — this applies the established language rather than matching a
 * picture: desk gradient background, Gochi Hand headers, --you/--them identity
 * colors for player names, gold for the primary action, the board's button
 * idiom (radius 6px, `0 3px 0` pressed shadow).
 *
 * Content/behavior preserved verbatim from the pre-refresh version, notably
 * the PR #371 additions: the AI persona nickname badge and the "Improvised"
 * badge (shown when the AI's plan didn't pan out and it adapted mid-turn).
 *
 * §8 iconography: kept only 🤖 (AI persona) and ✨ (Improvised) — both are
 * content-bearing badges the spec doesn't explicitly forbid. Removed the
 * one-off decorative emoji not sanctioned by §8's allowed list (⚡ charge,
 * 🎯 target, the cracked-card broken pip, bear-head logo): 🏠 on the primary
 * button, 📋/📖 on the mode toggle, ⏳ loading spinners, 💭 on AI reasoning
 * blocks, and the trailing 🤖 in the "AI decisions powered by" footer.
 */

import { useState, useEffect, useMemo } from 'react';
import type { GameState } from '../types/game';
import { generateNarrative } from '../api/gameService';
import { fetchAILogsForGame } from '../api/statsService';

interface VictoryScreenProps {
  gameState: GameState;
  onPlayAgain: () => void;
  /** Test/preview seam: when provided, skips the fetchAILogsForGame() call
   *  and renders this canned payload instead. Production callers never pass
   *  this — used by the /design.html harness fixtures (#victory, #defeat),
   *  which mirror DeckSelection's `cardsOverride` seam. */
  aiLogsOverride?: AILogData[];
}

// Import shared type from statsService
import type { AILogData } from '../api/statsService';
import { plannerModeLabel, plannerDisplayName } from '../utils/plannerMode';

export function VictoryScreen({ gameState, onPlayAgain, aiLogsOverride }: VictoryScreenProps) {
  const winnerPlayer = gameState.players[gameState.winner || ''];
  const playByPlay = useMemo(() => gameState.play_by_play || [], [gameState.play_by_play]);
  const [narrativeMode, setNarrativeMode] = useState(false);
  const [narrative, setNarrative] = useState<string>('');
  const [isLoadingNarrative, setIsLoadingNarrative] = useState(false);
  const [aiLogs, setAiLogs] = useState<AILogData[]>(aiLogsOverride ?? []);

  // Fetch AI logs for this game
  useEffect(() => {
    if (aiLogsOverride) return; // preview harness supplies logs directly
    if (gameState.game_id) {
      fetchAILogsForGame(gameState.game_id)
        .then((logs) => {
          // Ensure logs is an array
          const validLogs = Array.isArray(logs) ? logs : [];
          setAiLogs(validLogs);
        })
        .catch((error) => {
          console.error('[VictoryScreen] Failed to fetch AI logs:', error);
          // Silently fail - AI logs are supplementary
          setAiLogs([]);
        });
    }
  }, [gameState.game_id, aiLogsOverride]);

  // Load narrative when mode is switched
  useEffect(() => {
    if (narrativeMode && !narrative && playByPlay.length > 0) {
      setIsLoadingNarrative(true);
      generateNarrative(playByPlay)
        .then((narrativeText) => {
          setNarrative(narrativeText);
        })
        .catch((error) => {
          console.error('Failed to generate narrative:', error);
          alert('Failed to generate narrative story. Please try again.');
          setNarrativeMode(false); // Fall back to factual mode
        })
        .finally(() => {
          setIsLoadingNarrative(false);
        });
    }
  }, [narrativeMode, narrative, playByPlay]);

  // Group actions by turn and player, merging with AI logs
  // useMemo ensures this recomputes when aiLogs changes
  const groupedActions = useMemo(() => {
    const grouped: Record<string, { actions: typeof playByPlay; aiLog?: AILogData }> = {};

    // First, group play-by-play actions
    playByPlay.forEach((entry) => {
      const key = `${entry.turn}-${entry.player}`;
      if (!grouped[key]) {
        grouped[key] = { actions: [] };
      }
      grouped[key].actions.push(entry);
    });

    // Then merge AI logs into grouped actions (only if aiLogs is an array)
    if (Array.isArray(aiLogs) && aiLogs.length > 0) {
      aiLogs.forEach((log) => {
        // Find matching player name from gameState
        const playerName = gameState.players[log.player_id]?.name;
        if (playerName) {
          const key = `${log.turn_number}-${playerName}`;
          if (grouped[key]) {
            grouped[key].aiLog = log;
          }
        }
      });
    }

    return grouped;
  }, [playByPlay, aiLogs, gameState.players]);

  // Identity color for a player name in the recap — you = blue, them = purple.
  // The winner's own player_id isn't directly on Player, so match by name
  // against the local-ish convention used elsewhere on this screen (the
  // "human" player is whichever one is NOT flagged as AI-authored below).
  const isAiPlayerName = (playerName: string): boolean => {
    return aiLogs.some((log) => gameState.players[log.player_id]?.name === playerName) ||
      playByPlay.some((e) => e.player === playerName && e.reasoning !== undefined);
  };

  const nameColor = (playerName: string): string => (isAiPlayerName(playerName) ? 'var(--them)' : 'var(--you)');

  return (
    <div
      className="min-h-screen flex items-center justify-center relative overflow-auto"
      style={{
        padding: 'var(--spacing-component-lg)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      <div className="relative z-10 w-full max-w-5xl mx-auto">
        {/* Victory Header */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-card-name)',
              fontSize: 'clamp(36px, 8vw, 64px)',
              lineHeight: 1,
              marginBottom: 'var(--spacing-component-md)',
              color: 'var(--ink-text)',
            }}
          >
            Game Over
          </h1>
          <p
            style={{
              fontSize: 'clamp(20px, 4vw, 32px)',
              fontWeight: 900,
              marginBottom: 'var(--spacing-component-lg)',
              color: nameColor(winnerPlayer?.name || gameState.winner || ''),
            }}
          >
            {winnerPlayer?.name || gameState.winner} Wins!
          </p>
          <button
            onClick={onPlayAgain}
            style={{
              padding: 'var(--spacing-component-md) var(--spacing-component-xl)',
              minWidth: '250px',
              fontWeight: 900,
              fontSize: 'clamp(16px, 3vw, 20px)',
              borderRadius: '6px',
              border: 'none',
              background: 'var(--gold)',
              color: 'var(--desk-bottom)',
              boxShadow: '0 3px 0 rgba(0,0,0,.5)',
              cursor: 'pointer',
            }}
          >
            Back to Main Menu
          </button>
        </div>

        {/* Play-by-Play Summary */}
        {playByPlay.length > 0 && (
          <div
            className="modal-padding"
            style={{
              background: '#241E17',
              borderRadius: '8px',
              border: '1px solid rgba(242,193,78,.25)',
              boxShadow: '0 8px 24px rgba(0,0,0,.4)',
            }}
          >
            <div
              className="flex flex-col sm:flex-row justify-between items-start sm:items-center"
              style={{
                gap: 'var(--spacing-component-md)',
                marginBottom: 'var(--spacing-component-lg)',
                paddingBottom: 'var(--spacing-component-lg)',
                borderBottom: '1px solid rgba(237,232,222,.15)',
              }}
            >
              <h2 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', color: 'var(--ink-text)' }}>
                Game Summary
              </h2>

              {/* Mode Toggle */}
              <div className="flex items-center" style={{ gap: 'var(--spacing-component-md)' }}>
                <button
                  onClick={() => setNarrativeMode(false)}
                  style={{
                    borderRadius: '6px',
                    fontWeight: 700,
                    padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
                    border: 'none',
                    background: !narrativeMode ? 'var(--gold)' : 'rgba(237,232,222,.1)',
                    color: !narrativeMode ? 'var(--desk-bottom)' : 'var(--ink-muted)',
                    cursor: 'pointer',
                  }}
                >
                  Factual
                </button>
                <button
                  onClick={() => setNarrativeMode(true)}
                  disabled={isLoadingNarrative}
                  style={{
                    borderRadius: '6px',
                    fontWeight: 700,
                    padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
                    border: 'none',
                    background: narrativeMode ? 'var(--them)' : 'rgba(237,232,222,.1)',
                    color: narrativeMode ? 'var(--ink-text)' : 'var(--ink-muted)',
                    cursor: isLoadingNarrative ? 'wait' : 'pointer',
                    opacity: isLoadingNarrative ? 0.5 : 1,
                  }}
                >
                  {isLoadingNarrative ? 'Loading...' : 'Story Mode'}
                </button>
              </div>
            </div>

            {/* Narrative Mode */}
            {narrativeMode ? (
              <div>
                {isLoadingNarrative ? (
                  <div
                    className="text-center"
                    style={{ paddingTop: 'var(--spacing-component-xl)', paddingBottom: 'var(--spacing-component-xl)', color: 'var(--ink-faint)' }}
                  >
                    <p>Generating your epic bedtime story...</p>
                  </div>
                ) : narrative ? (
                  <div className="content-spacing" style={{ color: 'var(--ink-text)', lineHeight: 1.8, fontSize: 'clamp(15px, 2vw, 18px)' }}>
                    {narrative.split('\n\n').map((paragraph, idx) => (
                      <p key={idx} className="text-justify">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div
                    className="text-center"
                    style={{ paddingTop: 'var(--spacing-component-xl)', paddingBottom: 'var(--spacing-component-xl)', color: 'var(--ink-faint)' }}
                  >
                    <p>No narrative available</p>
                  </div>
                )}
              </div>
            ) : (
              /* Factual Mode */
              <div className="content-spacing">
                {Object.entries(groupedActions).map(([key, { actions, aiLog }]) => {
                  const firstAction = actions[0];
                  const isAI = firstAction.reasoning !== undefined || aiLog !== undefined;
                  const plannerMode = plannerModeLabel(aiLog?.turn_plan?.planner, aiLog?.ai_version);
                  const plannerNickname = plannerDisplayName(aiLog?.turn_plan?.planner, aiLog?.ai_version);
                  const hasPlan = !!aiLog?.turn_plan;
                  const isFallback = aiLog?.plan_execution_status === 'fallback';

                  return (
                    <div
                      key={key}
                      className="card-padding"
                      style={{
                        borderRadius: '6px',
                        borderLeft: `4px solid ${isAI ? 'var(--them)' : 'var(--you)'}`,
                        background: isAI ? 'rgba(180,142,222,.1)' : 'rgba(237,232,222,.04)',
                      }}
                    >
                      {/* Turn and Player Header */}
                      <div
                        className="flex items-center flex-wrap"
                        style={{
                          gap: 'var(--spacing-component-sm)',
                          marginBottom: 'var(--spacing-component-sm)',
                          paddingBottom: 'var(--spacing-component-xs)',
                          borderBottom: '1px solid rgba(237,232,222,.12)',
                        }}
                      >
                        <span
                          style={{
                            fontFamily: 'monospace',
                            fontSize: '11px',
                            borderRadius: '4px',
                            padding: 'var(--spacing-component-xs) var(--spacing-component-xs)',
                            background: 'rgba(237,232,222,.1)',
                            color: 'var(--ink-muted)',
                          }}
                        >
                          Turn {firstAction.turn}
                        </span>
                        <span style={{ fontWeight: 900, fontSize: 'clamp(15px, 2vw, 18px)', color: nameColor(firstAction.player) }}>
                          {firstAction.player}
                        </span>
                        {/* AI persona badge — player-facing nickname (raw planner
                            value stays in the admin data viewer) */}
                        {aiLog && (
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              borderRadius: '4px',
                              padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                              background: plannerMode !== 'per-action' ? 'var(--them)' : 'rgba(237,232,222,.1)',
                              color: plannerMode !== 'per-action' ? 'var(--ink-text)' : 'var(--ink-muted)',
                            }}
                            title="AI opponent"
                          >
                            🤖 {plannerNickname}
                          </span>
                        )}
                        {/* Improvised badge — the AI's plan didn't pan out and it
                            adapted mid-turn. Player-facing wording; the raw
                            fallback_reason stays in the admin data viewer. */}
                        {isFallback && (
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              borderRadius: '4px',
                              padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                              background: 'var(--gold)',
                              color: 'var(--desk-bottom)',
                            }}
                            title="The AI adapted its plan mid-turn"
                          >
                            ✨ Improvised
                          </span>
                        )}
                      </div>

                      {/* Turn Plan */}
                      {hasPlan && aiLog.turn_plan && (
                        <div
                          style={{
                            borderRadius: '6px',
                            border: '1px solid rgba(180,142,222,.35)',
                            background: 'rgba(180,142,222,.12)',
                            marginBottom: 'var(--spacing-component-sm)',
                            padding: 'var(--spacing-component-sm)',
                          }}
                        >
                          <div style={{ fontSize: '13px', marginBottom: 'var(--spacing-component-xs)', fontWeight: 700, color: 'var(--them)' }}>
                            Plan:
                          </div>
                          <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--ink-muted)' }}>
                            {aiLog.turn_plan.strategy}
                          </p>
                        </div>
                      )}

                      {/* Actions for this turn/player */}
                      <div className="content-spacing">
                        {actions
                          .filter((entry) => {
                            // The live plan announcement duplicates the "Plan"
                            // block above (both come from the same turn plan)
                            if (entry.action_type === 'strategy') return false;
                            // Filter out generic "ended their turn" messages
                            const desc = entry.description.toLowerCase();
                            return !(desc.includes('ended their turn') || desc.includes('ended turn'));
                          })
                          .map((entry, index) => (
                            <div key={index}>
                              {/* Action Description */}
                              <p style={{ paddingLeft: 'var(--spacing-component-xs)', lineHeight: 1.5, color: 'var(--ink-text)' }}>
                                • {entry.description}
                              </p>

                              {/* AI Reasoning */}
                              {entry.reasoning && (
                                <div
                                  style={{
                                    borderTop: '1px solid rgba(180,142,222,.3)',
                                    background: 'rgba(180,142,222,.08)',
                                    borderRadius: '4px',
                                    marginTop: 'var(--spacing-component-xs)',
                                    marginLeft: 'var(--spacing-component-sm)',
                                    paddingTop: 'var(--spacing-component-xs)',
                                    padding: 'var(--spacing-component-sm)',
                                  }}
                                >
                                  <p style={{ fontSize: '13px', fontStyle: 'italic', lineHeight: 1.5, color: 'var(--ink-muted)' }}>
                                    <span style={{ fontWeight: 700, fontStyle: 'normal', color: 'var(--them)' }}>AI Strategy:</span> {entry.reasoning}
                                  </p>
                                </div>
                              )}
                            </div>
                          ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* AI Endpoint Summary - Only show in factual mode */}
            {!narrativeMode && playByPlay.some((entry) => entry.ai_endpoint) && (
              <div
                className="text-center"
                style={{
                  marginTop: 'var(--spacing-component-xl)',
                  paddingTop: 'var(--spacing-component-lg)',
                  borderTop: '1px solid rgba(237,232,222,.15)',
                }}
              >
                <p style={{ fontSize: '13px', color: 'var(--ink-faint)' }}>
                  AI decisions powered by{' '}
                  <span style={{ fontWeight: 700, color: 'var(--them)' }}>
                    {Array.from(new Set(playByPlay.filter((e) => e.ai_endpoint).map((e) => e.ai_endpoint))).join(', ')}
                  </span>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

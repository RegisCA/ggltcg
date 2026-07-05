/**
 * GameMessages — the log strip (Paper & Ink §5.2).
 *
 * A paper surface sitting under the score chips (WP-2 #4: the log is the first
 * checkpoint when reconstructing the opponent's turn). Collapsed: a single
 * paper one-liner — TURN N · actor tick · latest event (or the "Opponent is
 * thinking" spinner) · ▾ log. Expanded (default, device-validated): the full
 * play-by-play on paper, grouped by turn, each entry ticked by actor
 * (you = blue, opponent = purple, system = neutral). Choice persists via
 * localStorage. All the opponent-turn behaviour (thinking spinner, streamed
 * entries, held height so the board doesn't bounce) is unchanged.
 *
 * Strip + tick values from the signed-off mockup (6a log).
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PlayByPlayEntry } from '../types/game';

const LOG_COLLAPSED_STORAGE_KEY = 'ggltcg-log-collapsed';

function loadCollapsedPreference(): boolean {
  try {
    return localStorage.getItem(LOG_COLLAPSED_STORAGE_KEY) === '1';
  } catch {
    return false; // storage blocked — default expanded
  }
}

/** Actor tick color (you = blue, opponent = purple, system = neutral). */
function tickColor(isHuman: boolean | null): string {
  if (isHuman === true) return 'var(--you)';
  if (isHuman === false) return 'var(--them)';
  return 'var(--paper-faint)';
}

/** Subtle on-paper tint behind an entry, matching its actor tick. */
function entryTint(isHuman: boolean | null): string {
  if (isHuman === true) return 'rgba(126,166,224,.12)';
  if (isHuman === false) return 'rgba(180,142,222,.12)';
  return 'rgba(0,0,0,.04)';
}

interface GameMessagesProps {
  messages: string[];
  isOpponentTurn?: boolean;
  isOpponentThinking?: boolean;
  isCompact?: boolean;
  playByPlay?: PlayByPlayEntry[];
  humanPlayerName?: string;
}

function Spinner({ size = 13 }: { size?: number }) {
  return (
    <svg
      style={{ width: `${size}px`, height: `${size}px`, flexShrink: 0 }}
      className="animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

export function GameMessages({
  messages,
  isOpponentTurn = false,
  isOpponentThinking = false,
  isCompact = false,
  playByPlay = [],
  humanPlayerName,
}: GameMessagesProps) {
  const [isCollapsed, setIsCollapsedState] = useState(loadCollapsedPreference);
  const [lastSeenCount, setLastSeenCount] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const setIsCollapsed = (value: boolean) => {
    setIsCollapsedState(value);
    try {
      localStorage.setItem(LOG_COLLAPSED_STORAGE_KEY, value ? '1' : '0');
    } catch {
      // storage blocked — preference just won't persist
    }
  };

  const isHumanActor = (actor: string | undefined | null): boolean | null => {
    if (!actor || !humanPlayerName) return null;
    return actor === humanPlayerName;
  };

  useEffect(() => {
    if (!isCollapsed) setLastSeenCount(messages.length);
  }, [isCollapsed, messages.length]);

  useEffect(() => {
    if (!isCollapsed && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [playByPlay.length, messages.length, isCollapsed]);

  const displayMessages = isCompact ? messages.slice(-5) : messages;
  const messageCount = messages.length;
  const newEventCount = Math.max(0, messageCount - lastSeenCount);
  const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const latestEntry = playByPlay.length > 0 ? playByPlay[playByPlay.length - 1] : null;

  return (
    <div
      style={{
        background: 'var(--paper)',
        color: 'var(--paper-ink-text)',
        borderRadius: '4px',
        boxShadow: '0 2px 0 rgba(0,0,0,.35)',
        overflow: 'hidden',
      }}
    >
      {/* Collapsed = the ticker one-liner; also the expand/collapse control. */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        aria-label={isCollapsed ? 'Expand game log' : 'Collapse game log'}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 10px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '11px',
          color: 'var(--paper-ink-text)',
          borderBottom: isCollapsed ? 'none' : '1px solid rgba(46,41,33,.12)',
        }}
      >
        {latestEntry && (
          <span style={{ fontWeight: 900, fontSize: '9px', letterSpacing: '.08em', color: 'var(--paper-faint)', flexShrink: 0 }}>
            TURN {latestEntry.turn}
          </span>
        )}

        {isCollapsed ? (
          isOpponentThinking ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--them)', minWidth: 0 }}>
              <Spinner size={12} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Opponent is thinking…</span>
            </span>
          ) : (
            <>
              <span style={{ width: '3px', height: '14px', borderRadius: '2px', background: tickColor(isHumanActor(latestEntry?.player)), flexShrink: 0 }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
                {latestEntry ? (
                  <>
                    <b>{latestEntry.player}</b> {latestEntry.description}
                  </>
                ) : (
                  latestMessage || 'No events yet'
                )}
              </span>
            </>
          )
        ) : (
          <span style={{ fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', fontSize: '9px', color: 'var(--paper-faint)' }}>
            Game log
          </span>
        )}

        {isCollapsed && newEventCount > 0 && (
          <span style={{ flexShrink: 0, borderRadius: '999px', background: 'var(--gold)', color: 'var(--desk-bottom)', fontWeight: 700, fontSize: '9px', padding: '1px 6px' }}>
            {newEventCount} new
          </span>
        )}

        <span style={{ marginLeft: 'auto', color: 'var(--paper-faint)', fontSize: '9px', flexShrink: 0 }}>
          {isCollapsed ? '▾ log' : '▴ log'}
        </span>
      </button>

      {/* Expanded — grows with the log up to a cap, then scrolls. During the
          opponent's turn it holds the cap height so streamed entries don't
          bounce the board. Re-fits when your turn starts. */}
      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div
              ref={scrollContainerRef}
              style={{
                overflowY: 'auto',
                height: isOpponentTurn ? (isCompact ? '150px' : '220px') : undefined,
                maxHeight: isCompact ? '150px' : '220px',
                padding: '6px 8px',
              }}
            >
              {displayMessages.length === 0 && !isOpponentThinking ? (
                <div style={{ color: 'var(--paper-faint)', fontStyle: 'italic', fontSize: '11px' }}>No events yet</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {playByPlay.length > 0 ? (
                    (() => {
                      const entriesToShow = isCompact ? playByPlay.slice(-5) : playByPlay;
                      const groupedByTurn: Record<number, typeof entriesToShow> = {};
                      entriesToShow.forEach((entry) => {
                        (groupedByTurn[entry.turn] ||= []).push(entry);
                      });

                      return Object.entries(groupedByTurn).map(([turn, entries]) => (
                        <div key={`turn-${turn}`}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: '4px 0 2px' }}>
                            <span style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--paper-faint)', flexShrink: 0 }}>
                              Turn {turn}
                            </span>
                            <div style={{ borderTop: '1px solid rgba(46,41,33,.12)', flex: 1 }} />
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            {entries.map((entry, idx) => {
                              const isHuman = isHumanActor(entry.player);
                              const isStrategy = entry.action_type === 'strategy';
                              return (
                                <div
                                  key={`${turn}-${idx}`}
                                  style={{
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    borderLeft: `3px solid ${tickColor(isHuman)}`,
                                    background: isStrategy ? 'rgba(180,142,222,.16)' : entryTint(isHuman),
                                    fontSize: isCompact ? '11px' : '12px',
                                    lineHeight: 1.35,
                                  }}
                                >
                                  {isStrategy ? (
                                    <>
                                      <span style={{ fontWeight: 700 }}>{entry.player}:</span>{' '}
                                      <span style={{ fontStyle: 'italic', color: 'var(--paper-muted)' }}>{entry.description}</span>
                                    </>
                                  ) : (
                                    <>
                                      <span style={{ fontWeight: 700 }}>{entry.player}:</span> {entry.description}
                                    </>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ));
                    })()
                  ) : (
                    displayMessages.map((msg, idx) => {
                      const isHuman = humanPlayerName && msg.startsWith(`${humanPlayerName}:`) ? true : msg.includes(':') ? false : null;
                      return (
                        <div
                          key={`${idx}-${msg.substring(0, 20)}`}
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            borderLeft: `3px solid ${tickColor(isHuman)}`,
                            background: entryTint(isHuman),
                            fontSize: isCompact ? '11px' : '12px',
                          }}
                        >
                          {msg}
                        </div>
                      );
                    })
                  )}

                  {isOpponentThinking && (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: 'rgba(180,142,222,.16)',
                        color: 'var(--them)',
                        fontSize: isCompact ? '11px' : '12px',
                        alignSelf: 'flex-start',
                      }}
                    >
                      <Spinner size={13} />
                      <span>{isCompact ? 'Opponent thinking…' : 'Opponent is thinking…'}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

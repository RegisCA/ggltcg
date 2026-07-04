/**
 * GameMessages Component
 *
 * The game log as a collapsible ticker strip (UI_REFRESH_2026_06 WP-2 #4:
 * the log is the first checkpoint when reconstructing the opponent's turn,
 * so it sits at the top of the board, always one glance away).
 *
 * Expanded (default — device review: "I'd pretty much always want it
 * expanded"): the full scrollable play-by-play, grouped by turn and
 * color-coded by actor. Collapsed: a single ticker line showing the latest
 * event — or the "Opponent is thinking" spinner while the AI acts — plus a
 * new-event count. The choice persists across games via localStorage.
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PlayByPlayEntry } from '../types/game';

const LOG_COLLAPSED_STORAGE_KEY = 'ggltcg-log-collapsed';

function loadCollapsedPreference(): boolean {
  try {
    return localStorage.getItem(LOG_COLLAPSED_STORAGE_KEY) === '1';
  } catch {
    return false; // e.g. storage blocked — fall back to expanded
  }
}

/** Per-actor chip styling so the log scans at a glance: your actions blue,
 *  the opponent's purple (matching the "thinking" indicator), system
 *  messages neutral. */
function actorStyle(isHuman: boolean | null): React.CSSProperties {
  if (isHuman === true) return { borderLeft: '3px solid #60a5fa' }; // blue-400
  if (isHuman === false) return { borderLeft: '3px solid #c084fc' }; // purple-400
  return { borderLeft: '3px solid #6b7280' }; // gray-500 (system)
}

function actorChipClass(isHuman: boolean | null): string {
  if (isHuman === true) return 'bg-blue-900';
  if (isHuman === false) return 'bg-purple-950';
  return 'bg-gray-700';
}

interface GameMessagesProps {
  messages: string[];
  /** True for the opponent's whole turn. The AI turn is a *sequence* of
   *  /ai-turn requests, so mutation-pending state flickers off between
   *  actions — the height freeze keys on this instead, spanning the gaps. */
  isOpponentTurn?: boolean;
  /** True only for the turn's thinking phase: from the opponent's turn
   *  starting until their first entry (normally the plan announcement)
   *  lands in the log. After that the streaming entries are the feedback —
   *  the spinner would just be noise over the acting phase. */
  isOpponentThinking?: boolean;
  isCompact?: boolean;  // Tighter type/spacing at phone widths
  playByPlay?: PlayByPlayEntry[];  // Full play-by-play with reasoning
  /** Display name of the local player, for per-actor color coding */
  humanPlayerName?: string;
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
  const [frozenHeight, setFrozenHeight] = useState<number | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const setIsCollapsed = (value: boolean) => {
    setIsCollapsedState(value);
    try {
      localStorage.setItem(LOG_COLLAPSED_STORAGE_KEY, value ? '1' : '0');
    } catch {
      // storage blocked — preference just won't persist
    }
  };

  /** null = system/unattributed message */
  const isHumanActor = (actor: string | undefined | null): boolean | null => {
    if (!actor || !humanPlayerName) return null;
    return actor === humanPlayerName;
  };

  // Update last seen count when expanded
  useEffect(() => {
    if (!isCollapsed) {
      setLastSeenCount(messages.length);
    }
  }, [isCollapsed, messages.length]);

  // Freeze the expanded log's height for the duration of the opponent's
  // turn: entries stream in mid-turn (2s poll), and letting the panel
  // re-fit per entry bounces the whole board below it. The held height
  // releases when the turn ends — the one moment the board is changing
  // anyway. New entries stay visible via the auto-scroll below.
  useEffect(() => {
    if (isOpponentTurn && !isCollapsed && scrollContainerRef.current) {
      // isCompact dep: re-capture when crossing the phone breakpoint, whose
      // max-height cap differs — a stale frozen height would fight it
      setFrozenHeight(scrollContainerRef.current.offsetHeight);
    } else {
      setFrozenHeight(null);
    }
  }, [isOpponentTurn, isCollapsed, isCompact]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (!isCollapsed && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [playByPlay.length, messages.length, isCollapsed]);

  // In compact mode, show fewer messages by default
  const displayMessages = isCompact ? messages.slice(-5) : messages;
  const messageCount = messages.length;
  const newEventCount = Math.max(0, messageCount - lastSeenCount);
  const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;

  return (
    <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
      {/* Header - Always visible, clickable to toggle. When collapsed it IS
          the ticker: latest event (or the AI-thinking spinner) inline. */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        aria-label={isCollapsed ? "Expand game log" : "Collapse game log"}
        className="w-full flex items-center justify-between bg-gray-900 hover:bg-gray-800 transition-colors"
        style={{
          padding: isCompact ? 'var(--spacing-component-xs) var(--spacing-component-sm)' : 'var(--spacing-component-sm) var(--spacing-component-md)',
          borderBottom: !isCollapsed ? '1px solid rgb(55 65 81)' : 'none',
          gap: 'var(--spacing-component-sm)'
        }}
      >
        <div className="flex items-center" style={{ gap: 'var(--spacing-component-xs)', minWidth: 0 }}>
          <span className={`text-gray-400 font-medium flex-shrink-0 ${isCompact ? 'text-xs' : 'text-sm'}`}>
            Game Log
          </span>
          {isCollapsed && newEventCount > 0 && (
            <span
              className="rounded-full bg-amber-900 text-amber-300 font-semibold flex-shrink-0"
              style={{
                padding: '2px var(--spacing-component-xs)',
                fontSize: isCompact ? '10px' : '0.75rem'
              }}
            >
              {newEventCount} new
            </span>
          )}
          {isCollapsed && (
            isOpponentThinking ? (
              <span
                className={`inline-flex items-center text-purple-300 ${isCompact ? 'text-xs' : 'text-sm'}`}
                style={{ gap: 'var(--spacing-component-xs)', minWidth: 0 }}
              >
                <svg
                  style={{ width: isCompact ? '12px' : '14px', height: isCompact ? '12px' : '14px', flexShrink: 0 }}
                  className="animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="truncate">Opponent is thinking...</span>
              </span>
            ) : latestMessage && (
              <span className={`text-gray-300 truncate ${isCompact ? 'text-xs' : 'text-sm'}`}>
                {latestMessage}
              </span>
            )
          )}
        </div>
        <svg
          aria-hidden="true"
          className="text-gray-400 flex-shrink-0 transition-transform duration-200"
          style={{
            width: isCompact ? '12px' : '16px',
            height: isCompact ? '12px' : '16px',
            transform: isCollapsed ? 'none' : 'rotate(180deg)'
          }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      </button>

      {/* Collapsible Content — grows with the log up to a cap (a short log
          shouldn't reserve a fixed panel height above the board), then the
          inner container scrolls */}
      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div
              ref={scrollContainerRef}
              style={{
                overflowY: 'auto',
                height: frozenHeight !== null ? `${frozenHeight}px` : undefined,
                maxHeight: isCompact ? '150px' : '220px',
                padding: isCompact ? 'var(--spacing-component-xs) var(--spacing-component-sm)' : 'var(--spacing-component-xs) var(--spacing-component-sm)'
              }}
            >
              {displayMessages.length === 0 && !isOpponentThinking ? (
                <div className={`text-gray-500 italic ${isCompact ? 'text-xs' : 'text-sm'}`}>
                  No messages yet
                </div>
              ) : (
                <div className="space-y-1">
                  {/* If we have play-by-play data with reasoning, use it */}
                  {playByPlay.length > 0 ? (
                    (() => {
                      // Group entries by turn for visual separation
                      const entriesToShow = isCompact ? playByPlay.slice(-5) : playByPlay;
                      const groupedByTurn: Record<number, typeof entriesToShow> = {};
                      
                      entriesToShow.forEach(entry => {
                        if (!groupedByTurn[entry.turn]) {
                          groupedByTurn[entry.turn] = [];
                        }
                        groupedByTurn[entry.turn].push(entry);
                      });
                      
                      return Object.entries(groupedByTurn).map(([turn, entries]) => (
                        <div key={`turn-${turn}`}>
                          {/* Turn label doubles as the group separator —
                              scanning for "what happened on turn N" was the
                              log's main job in observed play (WP-2 #4) */}
                          <div
                            className="flex items-center text-gray-500"
                            style={{ gap: 'var(--spacing-component-xs)', margin: '4px 0 2px' }}
                          >
                            <span className="text-[10px] font-bold uppercase tracking-wider flex-shrink-0">
                              Turn {turn}
                            </span>
                            <div className="border-t border-gray-700 flex-1" />
                          </div>

                          {/* Turn entries */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            {entries.map((entry, idx) => {
                              const entryKey = `${turn}-${idx}`;
                              const isHuman = isHumanActor(entry.player);

                              // The AI's once-per-turn plan announcement
                              // (backend action_type "strategy") reads as
                              // commentary, not an action: brighter purple,
                              // italic, 💭 — mirrors the recap's plan block
                              if (entry.action_type === 'strategy') {
                                return (
                                  <div
                                    key={entryKey}
                                    className="bg-purple-900 rounded overflow-hidden"
                                    style={{
                                      padding: isCompact ? '2px 6px' : '2px 8px',
                                      borderLeft: '3px solid #c084fc',
                                    }}
                                  >
                                    <div className={`text-purple-100 ${isCompact ? 'text-xs' : 'text-sm'}`}>
                                      <span className="font-semibold not-italic">💭 {entry.player}:</span>{' '}
                                      <span className="italic">{entry.description}</span>
                                    </div>
                                  </div>
                                );
                              }

                              return (
                                <div
                                  key={entryKey}
                                  className={`${actorChipClass(isHuman)} rounded overflow-hidden`}
                                  style={{
                                    padding: isCompact ? '2px 6px' : '2px 8px',
                                    ...actorStyle(isHuman),
                                  }}
                                >
                                  <div className={isCompact ? 'text-xs' : 'text-sm'}>
                                    <span className="font-semibold">{entry.player}:</span> {entry.description}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ));
                    })()
                  ) : (
                    /* Fallback to simple messages if no play-by-play data.
                       Attribute by the "Name: ..." prefix convention. */
                    displayMessages.map((msg, idx) => {
                      const isHuman = humanPlayerName && msg.startsWith(`${humanPlayerName}:`)
                        ? true
                        : msg.includes(':') ? false : null;
                      return (
                        <div
                          key={`${idx}-${msg.substring(0, 20)}`}
                          className={`${actorChipClass(isHuman)} rounded`}
                          style={{
                            padding: isCompact ? '2px 6px' : '2px 8px',
                            fontSize: isCompact ? '0.75rem' : '0.875rem',
                            ...actorStyle(isHuman),
                          }}
                        >
                          {msg}
                        </div>
                      );
                    })
                  )}
                  
                  {isOpponentThinking && (
                    <div
                      className="bg-purple-900 rounded inline-flex items-center"
                      style={{
                        padding: isCompact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-sm)',
                        gap: isCompact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-sm)',
                        fontSize: isCompact ? '0.75rem' : '0.875rem'
                      }}
                    >
                      <svg 
                        style={{ 
                          width: isCompact ? '12px' : '14px', 
                          height: isCompact ? '12px' : '14px', 
                          flexShrink: 0 
                        }}
                        className="animate-spin text-purple-300" 
                        xmlns="http://www.w3.org/2000/svg" 
                        fill="none" 
                        viewBox="0 0 24 24"
                      >
                        <circle 
                          className="opacity-25" 
                          cx="12" cy="12" r="10" 
                          stroke="currentColor" 
                          strokeWidth="4"
                        />
                        <path 
                          className="opacity-75" 
                          fill="currentColor" 
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      <span>{isCompact ? 'Opponent thinking...' : 'Opponent is thinking...'}</span>
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

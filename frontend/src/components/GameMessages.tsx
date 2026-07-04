/**
 * GameMessages Component
 *
 * The game log as a collapsible ticker strip (UI_REFRESH_2026_06 WP-2 #4:
 * the log is the first checkpoint when reconstructing the opponent's turn,
 * so it sits at the top of the board, always one glance away).
 *
 * Collapsed (default): a single line showing the latest event — or the
 * "Opponent is thinking" spinner while the AI acts — plus a new-event count.
 * Expanded: the full scrollable play-by-play, grouped by turn.
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PlayByPlayEntry } from '../types/game';

interface GameMessagesProps {
  messages: string[];
  isAIThinking?: boolean;
  isCompact?: boolean;  // Tighter type/spacing at phone widths
  playByPlay?: PlayByPlayEntry[];  // Full play-by-play with reasoning
}

export function GameMessages({
  messages,
  isAIThinking = false,
  isCompact = false,
  playByPlay = []
}: GameMessagesProps) {
  // Ticker: collapsed by default everywhere — the header line always shows
  // the latest event, so nothing is lost until the player wants history
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [lastSeenCount, setLastSeenCount] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Update last seen count when expanded
  useEffect(() => {
    if (!isCollapsed) {
      setLastSeenCount(messages.length);
    }
  }, [isCollapsed, messages.length]);

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
            isAIThinking ? (
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

      {/* Collapsible Content */}
      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ 
              height: isCompact ? '150px' : '350px',
              opacity: 1 
            }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
            style={{
              maxHeight: isCompact ? '150px' : '350px'
            }}
          >
            <div
              ref={scrollContainerRef}
              className="h-full"
              style={{ 
                overflowY: 'auto',
                padding: isCompact ? 'var(--spacing-component-xs) var(--spacing-component-sm)' : 'var(--spacing-component-md)'
              }}
            >
              {displayMessages.length === 0 && !isAIThinking ? (
                <div className={`text-gray-500 italic ${isCompact ? 'text-xs' : 'text-sm'}`}>
                  No messages yet
                </div>
              ) : (
                <div className={isCompact ? 'space-y-1' : 'space-y-2'}>
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
                      
                      return Object.entries(groupedByTurn).map(([turn, entries], turnIdx) => (
                        <div key={`turn-${turn}`}>
                          {/* Turn separator */}
                          {turnIdx > 0 && (
                            <div 
                              className="border-t border-gray-700"
                              style={{ 
                                marginTop: 'var(--spacing-component-xs)', 
                                marginBottom: 'var(--spacing-component-xs)',
                                paddingTop: isCompact ? '4px' : 'var(--spacing-component-xs)'
                              }}
                            />
                          )}
                          
                          {/* Turn entries */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '4px' : 'var(--spacing-component-xs)' }}>
                            {entries.map((entry, idx) => {
                              const entryKey = `${turn}-${idx}`;
                              
                              return (
                                <div 
                                  key={entryKey}
                                  className="bg-blue-900 rounded overflow-hidden"
                                  style={{
                                    padding: isCompact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-sm)'
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
                    /* Fallback to simple messages if no play-by-play data */
                    displayMessages.map((msg, idx) => (
                      <div 
                        key={`${idx}-${msg.substring(0, 20)}`} 
                        className="bg-blue-900 rounded"
                        style={{
                          padding: isCompact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-sm)',
                          fontSize: isCompact ? '0.75rem' : '0.875rem'
                        }}
                      >
                        {msg}
                      </div>
                    ))
                  )}
                  
                  {isAIThinking && (
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

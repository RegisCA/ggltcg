/**
 * BreakZoneDisplay Component
 * Shows a player's break zone with small card displays.
 *
 * Cards never overlap (the old offset-stack rendering made 2+ cards
 * unreadable — UI_REFRESH_2026_06 WP-1 #2 / WP-2 #8):
 * - default: cards wrap into a grid, every card fully readable
 * - compact (narrow fixed-width column): most recent card + a "view all"
 *   button that opens a modal with the full list
 */

import { useState } from 'react';
import { CardDisplay } from './CardDisplay';
import { Modal } from './ui/Modal';
import type { Card } from '../types/game';

interface BreakZoneDisplayProps {
  cards: Card[];
  playerName: string;
  isCompact?: boolean;  // Narrow fixed-width column (tablet/mobile layouts)
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function BreakZoneDisplay({
  cards,
  playerName,
  isCompact = false,
  enableLayoutAnimation = false,
}: BreakZoneDisplayProps) {
  const cardList = cards || [];
  const [isListOpen, setIsListOpen] = useState(false);

  const minHeight = isCompact ? '180px' : '200px';
  // Compact mode only has room for one card; the newest break is the one
  // players look for first when reconstructing what just happened.
  const newestCard = cardList[cardList.length - 1];
  const hiddenCount = cardList.length - 1;

  return (
    <div className="bg-gray-800 rounded border border-gray-700" style={{ minHeight, padding: 'var(--spacing-component-sm)' }}>
      <div className="text-sm text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
        {playerName} - BREAK ZONE ({cardList.length})
      </div>

      {cardList.length === 0 ? (
        <div className="text-center text-gray-600 italic text-sm" style={{ padding: 'var(--spacing-component-md) 0' }}>
          No broken cards
        </div>
      ) : isCompact ? (
        <div className="flex flex-col items-start" style={{ gap: 'var(--spacing-component-xs)' }}>
          <CardDisplay
            card={newestCard}
            size="small"
            enableLayoutAnimation={enableLayoutAnimation}
          />
          {hiddenCount > 0 && (
            <button
              onClick={() => setIsListOpen(true)}
              className="w-full text-xs font-bold text-gray-300 bg-gray-700 hover:bg-gray-600 rounded border border-gray-600 transition-colors"
              style={{ padding: 'var(--spacing-component-xs)' }}
              aria-label={`View all ${cardList.length} broken cards`}
            >
              +{hiddenCount} more — view all
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap" style={{ gap: 'var(--spacing-component-xs)' }}>
          {cardList.map((card) => (
            <CardDisplay
              key={card.id}
              card={card}
              size="small"
              enableLayoutAnimation={enableLayoutAnimation}
            />
          ))}
        </div>
      )}

      {/* Full-list modal for compact mode. Cards here intentionally skip
          layout animation: the newest card is also rendered in the zone and
          duplicate framer-motion layoutIds would conflict. */}
      <Modal
        isOpen={isListOpen}
        onClose={() => setIsListOpen(false)}
        title={`${playerName} break zone`}
      >
        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
          <h3 className="font-bold text-lg">
            {playerName} - Break Zone ({cardList.length})
          </h3>
          <button
            onClick={() => setIsListOpen(false)}
            className="text-gray-400 hover:text-white text-xl font-bold rounded"
            style={{ padding: '0 var(--spacing-component-xs)' }}
            aria-label="Close break zone list"
          >
            ✕
          </button>
        </div>
        <div className="flex flex-wrap overflow-y-auto" style={{ gap: 'var(--spacing-component-sm)' }}>
          {cardList.map((card) => (
            <CardDisplay key={card.id} card={card} size="small" disableDetailModal={true} />
          ))}
        </div>
      </Modal>
    </div>
  );
}

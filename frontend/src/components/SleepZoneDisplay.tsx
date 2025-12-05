/**
 * SleepZoneDisplay Component
 * Shows a player's sleep zone with small card displays
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface SleepZoneDisplayProps {
  cards: Card[];
  playerName: string;
  isCompact?: boolean;  // Reduce spacing in tablet mode
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function SleepZoneDisplay({ 
  cards, 
  playerName, 
  isCompact = false,
  enableLayoutAnimation = false,
}: SleepZoneDisplayProps) {
  const cardList = cards || [];
  
  // Card layout constants from design system (CSS variables)
  // Small card height: 164px (from --spacing-card-small-h)
  const CARD_SMALL_HEIGHT = 164;
  // Stack offsets from CSS: --card-stack-offset-vertical(-compact), --card-stack-offset-horizontal(-compact)
  const stackOffset = isCompact ? 22 : 28;  // Matches CSS variables
  const horizontalOffset = isCompact ? 18 : 25;  // Matches CSS variables
  
  // Calculate total stack height: first card full height + additional cards at offset
  const stackHeight = cardList.length > 0 ? CARD_SMALL_HEIGHT + (cardList.length - 1) * stackOffset : CARD_SMALL_HEIGHT;
  const minHeight = isCompact ? '180px' : '200px';
  
  return (
    <div className="bg-gray-800 rounded border border-gray-700" style={{ minHeight, padding: 'var(--spacing-component-sm)' }}>
      <div className="text-sm text-gray-400" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
        {playerName} - SLEEP ZONE ({cardList.length})
      </div>
      
      {cardList.length === 0 ? (
        <div className="text-center text-gray-600 italic text-sm" style={{ padding: 'var(--spacing-component-md) 0' }}>
          No sleeping cards
        </div>
      ) : (
        <div style={{ position: 'relative', height: `${stackHeight}px` }}>
          {cardList.map((card, index) => (
            <div
              key={card.id}
              style={{ 
                position: 'absolute',
                top: `${index * stackOffset}px`,
                left: `${index * horizontalOffset}px`,
                zIndex: index,
              }}
            >
              <CardDisplay
                card={card}
                size="small"
                enableLayoutAnimation={enableLayoutAnimation}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

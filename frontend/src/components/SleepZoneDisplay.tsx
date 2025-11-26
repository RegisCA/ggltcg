/**
 * SleepZoneDisplay Component
 * Shows a player's sleep zone with small card displays
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface SleepZoneDisplayProps {
  cards: Card[];
  playerName: string;
  compact?: boolean;  // Reduce spacing in tablet mode
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function SleepZoneDisplay({ 
  cards, 
  playerName, 
  compact = false,
  enableLayoutAnimation = false,
}: SleepZoneDisplayProps) {
  const cardList = cards || [];
  // Calculate height: base card height (164px for small) + offset for each additional card
  const stackOffset = compact ? 22 : 28;
  const horizontalOffset = compact ? 18 : 25;
  const stackHeight = cardList.length > 0 ? 164 + (cardList.length - 1) * stackOffset : 160;
  const minHeight = compact ? '180px' : '200px';
  
  return (
    <div className="bg-gray-800 rounded p-3 border border-gray-700" style={{ minHeight }}>
      <div className="text-sm text-gray-400 mb-2">
        {playerName} - SLEEP ZONE ({cardList.length})
      </div>
      
      {cardList.length === 0 ? (
        <div className="text-center text-gray-600 py-4 italic text-sm">
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

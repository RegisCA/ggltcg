/**
 * SleepZoneDisplay Component
 * Shows a player's sleep zone with small card displays
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface SleepZoneDisplayProps {
  cards: Card[];
  playerName: string;
}

export function SleepZoneDisplay({ cards, playerName }: SleepZoneDisplayProps) {
  const cardList = cards || [];
  // Calculate height: base card height (164px for small) + offset for each additional card
  const stackHeight = cardList.length > 0 ? 164 + (cardList.length - 1) * 28 : 160;
  
  return (
    <div className="bg-gray-800 rounded p-3 border border-gray-700" style={{ minHeight: '200px' }}>
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
                top: `${index * 28}px`,
                left: `${index * 25}px`,
                zIndex: index,
              }}
            >
              <CardDisplay
                card={card}
                size="small"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

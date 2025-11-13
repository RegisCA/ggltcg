/**
 * HandZone Component
 * Displays a player's hand of cards
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface HandZoneProps {
  cards: Card[];
  selectedCard?: string;
  onCardClick?: (cardName: string) => void;
}

export function HandZone({ cards, selectedCard, onCardClick }: HandZoneProps) {
  const cardList = cards || [];
  
  return (
    <div className="bg-blue-950 rounded border-2 border-blue-700 flex">
      {/* Vertical Label */}
      <div className="flex items-center justify-center bg-blue-900 px-2 rounded-l border-r border-blue-700">
        <div className="text-xs text-gray-400 font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          HAND ({cardList.length})
        </div>
      </div>
      
      {/* Cards Area */}
      <div className="flex-1 p-3">
        {cardList.length === 0 ? (
          <div className="text-center text-gray-600 italic text-sm" style={{ minHeight: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            No cards in hand
          </div>
        ) : (
          <div className="flex gap-2">
            {cardList.map((card) => (
              <CardDisplay
                key={`${card.name}-${card.zone}`}
                card={card}
                size="medium"
                isSelected={selectedCard === card.name}
                isClickable={!!onCardClick}
                onClick={onCardClick ? () => onCardClick(card.name) : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

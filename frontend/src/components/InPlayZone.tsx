/**
 * InPlayZone Component
 * Displays cards that are in play for a player
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface InPlayZoneProps {
  cards: Card[];
  playerName: string;
  isHuman?: boolean;
  selectedCard?: string;  // Now expects card ID instead of card name
  onCardClick?: (cardId: string) => void;
  cardSize?: 'small' | 'medium';  // Responsive card size
}

export function InPlayZone({ cards, isHuman = false, selectedCard, onCardClick, cardSize = 'medium' }: InPlayZoneProps) {
  const cardList = cards || [];
  const minHeight = cardSize === 'small' ? '170px' : '240px';
  
  return (
    <div className="bg-gray-800 rounded border border-gray-700 flex">
      {/* Vertical Label */}
      <div className="flex items-center justify-center bg-gray-900 px-2 rounded-l border-r border-gray-700">
        <div className="text-xs text-gray-400 font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          IN PLAY ({cardList.length})
        </div>
      </div>
      
      {/* Cards Area */}
      <div className="flex-1 p-3">
        {cardList.length === 0 ? (
          <div className="text-center text-gray-600 italic text-sm" style={{ minHeight, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            No cards in play
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {cardList.map((card) => (
              <CardDisplay
                key={card.id}
                card={card}
                size={cardSize}
                isSelected={selectedCard === card.id}
                isClickable={isHuman && !!onCardClick}
                onClick={isHuman && onCardClick ? () => onCardClick(card.id) : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

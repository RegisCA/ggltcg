/**
 * HandZone Component
 * Displays a player's hand of cards with playability indicators
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface HandZoneProps {
  cards: Card[];
  selectedCard?: string;  // Now expects card ID instead of card name
  onCardClick?: (cardId: string) => void;
  playableCardIds?: string[];  // IDs of cards that can be played this turn
  isPlayerTurn?: boolean;  // Whether it's the player's turn
  cardSize?: 'small' | 'medium';  // Responsive card size
}

export function HandZone({ 
  cards, 
  selectedCard, 
  onCardClick, 
  playableCardIds = [],
  isPlayerTurn = false,
  cardSize = 'medium',
}: HandZoneProps) {
  const cardList = cards || [];
  const minHeight = cardSize === 'small' ? '170px' : '240px';
  
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
          <div className="text-center text-gray-600 italic text-sm" style={{ minHeight, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            No cards in hand
          </div>
        ) : (
          <div className="flex gap-2">
            {cardList.map((card) => {
              // Card is playable if it's in the playable list OR it's not the player's turn (don't dim during opponent's turn)
              const isPlayable = !isPlayerTurn || playableCardIds.includes(card.id);
              return (
                <CardDisplay
                  key={card.id}
                  card={card}
                  size={cardSize}
                  isSelected={selectedCard === card.id}
                  isClickable={!!onCardClick}
                  isUnplayable={isPlayerTurn && !isPlayable}
                  onClick={onCardClick ? () => onCardClick(card.id) : undefined}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

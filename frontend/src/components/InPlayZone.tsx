/**
 * InPlayZone Component
 * Displays cards that are in play for a player
 * 
 * Supports direct card interaction for tussles and activated abilities.
 * Cards that have available actions show a subtle glow when hovered.
 */

import { CardDisplay } from './CardDisplay';
import type { Card } from '../types/game';

interface InPlayZoneProps {
  cards: Card[];
  playerName: string;
  isHuman?: boolean;
  selectedCard?: string;  // Now expects card ID instead of card name
  onCardClick?: (cardId: string) => void;
  actionableCardIds?: string[];  // IDs of cards that can perform actions (tussle/ability)
  isPlayerTurn?: boolean;  // Whether it's the player's turn
  cardSize?: 'small' | 'medium';  // Responsive card size
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function InPlayZone({ 
  cards, 
  isHuman = false, 
  selectedCard, 
  onCardClick, 
  actionableCardIds = [],
  isPlayerTurn = false,
  cardSize = 'medium',
  enableLayoutAnimation = false,
}: InPlayZoneProps) {
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
            {cardList.map((card) => {
              // Card is actionable if it's in the actionable list (can tussle or use ability)
              const isActionable = isPlayerTurn && actionableCardIds.includes(card.id);
              // Card is clickable if it's the human's zone, has a click handler, AND has an action
              // Non-actionable cards are still visible but not clickable
              const isClickable = isHuman && !!onCardClick && isActionable;
              
              return (
                <CardDisplay
                  key={card.id}
                  card={card}
                  size={cardSize}
                  isSelected={selectedCard === card.id}
                  isClickable={isClickable}
                  isHighlighted={isActionable}
                  onClick={isClickable ? () => onCardClick(card.id) : undefined}
                  enableLayoutAnimation={enableLayoutAnimation}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

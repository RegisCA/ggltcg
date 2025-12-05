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
  compact?: boolean;  // Compact mode for landscape tablets - scrollable horizontal
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function HandZone({ 
  cards, 
  selectedCard, 
  onCardClick, 
  playableCardIds = [],
  isPlayerTurn = false,
  cardSize = 'medium',
  compact = false,
  enableLayoutAnimation = false,
}: HandZoneProps) {
  const cardList = cards || [];
  // Reduce minHeight to allow more flexible vertical space distribution
  const minHeight = compact ? '130px' : (cardSize === 'small' ? '140px' : '180px');
  
  return (
    <div className="bg-blue-950 rounded border-2 border-blue-700 flex">
      {/* Vertical Label */}
      <div 
        className="flex items-center justify-center bg-blue-900 rounded-l border-r border-blue-700"
        style={{ paddingLeft: 'var(--spacing-component-xs)', paddingRight: 'var(--spacing-component-xs)' }}
      >
        <div className="text-xs text-gray-400 font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          HAND ({cardList.length})
        </div>
      </div>
      
      {/* Cards Area */}
      <div className={`flex-1 ${compact ? 'overflow-x-auto' : ''}`} style={{ padding: compact ? 'var(--spacing-component-xs)' : 'var(--spacing-component-sm)' }}>
        {cardList.length === 0 ? (
          <div className="text-center text-gray-600 italic text-sm" style={{ minHeight, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            No cards in hand
          </div>
        ) : (
          <div 
            className="flex flex-wrap"
            style={{ gap: 'var(--spacing-component-xs)' }}
          >
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

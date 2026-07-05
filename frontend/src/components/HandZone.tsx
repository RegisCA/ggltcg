/**
 * HandZone Component
 * Displays a player's hand of cards with playability indicators
 */

import { CardDisplay } from './CardDisplay';
import { cardGridTemplateColumns } from '../utils/cardGridTracks';
import type { Card } from '../types/game';

interface HandZoneProps {
  cards: Card[];
  selectedCard?: string;  // Now expects card ID instead of card name
  onCardClick?: (cardId: string) => void;
  playableCardIds?: string[];  // IDs of cards that can be played this turn
  isPlayerTurn?: boolean;  // Whether it's the player's turn
  size?: 'small' | 'medium';  // Responsive card size (matches CardDisplay)
  isCompact?: boolean;  // Compact mode for landscape tablets - scrollable horizontal
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
  /** Per-card targeting side (card ID → side), shown as a hint tag (WP-2 #5) */
  targetHints?: Record<string, 'yours' | 'theirs' | 'either'>;
}

export function HandZone({ 
  cards, 
  selectedCard, 
  onCardClick, 
  playableCardIds = [],
  isPlayerTurn = false,
  size = 'medium',
  isCompact = false,
  enableLayoutAnimation = false,
  targetHints = {},
}: HandZoneProps) {
  const cardList = cards || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Zone label (§5) — "Your hand · N", no dot (the hand is always yours). */}
      <div style={{ marginBottom: '6px' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
          Your hand · {cardList.length}
        </span>
      </div>

      {cardList.length === 0 ? (
        <div style={{ minHeight: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontStyle: 'italic', color: 'var(--ink-faint)' }}>
          No cards in hand
        </div>
      ) : (
          /* Compact mode keeps fixed-width cards in a horizontal scroll row;
             otherwise an auto-fill grid lets cards widen (up to a max) so
             names get the available space instead of truncating */
          <div
            className={isCompact ? 'flex flex-wrap' : ''}
            style={
              isCompact
                ? { gap: '8px', overflowX: 'auto' }
                : {
                    display: 'grid',
                    gridTemplateColumns: cardGridTemplateColumns(size),
                    gridAutoRows: '1fr',
                    gap: '8px',
                  }
            }
          >
            {cardList.map((card) => {
              // Card is playable if it's in the playable list OR it's not the player's turn (don't dim during opponent's turn)
              const isPlayable = !isPlayerTurn || playableCardIds.includes(card.id);
              return (
                <CardDisplay
                  key={card.id}
                  card={card}
                  size={size}
                  fluid={!isCompact}
                  isSelected={selectedCard === card.id}
                  isClickable={!!onCardClick}
                  isUnplayable={isPlayerTurn && !isPlayable}
                  onClick={onCardClick ? () => onCardClick(card.id) : undefined}
                  enableLayoutAnimation={enableLayoutAnimation}
                  targetHint={targetHints[card.id]}
                />
              );
            })}
          </div>
        )}
    </div>
  );
}

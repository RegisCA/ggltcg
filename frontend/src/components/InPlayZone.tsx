/**
 * InPlayZone Component
 * Displays cards that are in play for a player
 * 
 * Supports direct card interaction for tussles and activated abilities.
 * Cards that have available actions show a subtle glow when hovered.
 */

import { CardDisplay } from './CardDisplay';
import { cardGridTemplateColumns } from '../utils/cardGridTracks';
import type { Card } from '../types/game';

interface InPlayZoneProps {
  cards: Card[];
  playerName: string;
  isHuman?: boolean;
  selectedCard?: string;  // Now expects card ID instead of card name
  onCardClick?: (cardId: string) => void;
  actionableCardIds?: string[];  // IDs of cards that can perform actions (tussle/ability)
  isPlayerTurn?: boolean;  // Whether it's the player's turn
  size?: 'small' | 'medium';  // Responsive card size (matches CardDisplay)
  enableLayoutAnimation?: boolean;  // Enable smooth zone transitions
}

export function InPlayZone({
  cards,
  playerName,
  isHuman = false,
  selectedCard,
  onCardClick,
  actionableCardIds = [],
  isPlayerTurn = false,
  size = 'medium',
  enableLayoutAnimation = false,
}: InPlayZoneProps) {
  const cardList = cards || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Zone header (§5): color dot (you=blue / them=purple) + NAME · IN PLAY.
          Zones sit side by side (opponent | you), so position alone no longer
          says whose board this is. */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px', marginBottom: '6px' }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isHuman ? 'var(--you)' : 'var(--them)', flexShrink: 0 }} />
        <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
          {playerName} · In play
        </span>
      </div>

      {cardList.length === 0 ? (
        <div style={{ minHeight: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontStyle: 'italic', color: 'var(--ink-faint)' }}>
          No cards in play
        </div>
      ) : (
        /* auto-fill grid, equal-height rows (grid-auto-rows:1fr) so cards in a
           column stay even; track sizing shared with HandZone. */
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: cardGridTemplateColumns(size),
              gridAutoRows: '1fr',
              gap: '8px',
              flex: 1,
            }}
          >
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
                  size={size}
                  fluid={true}
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
  );
}

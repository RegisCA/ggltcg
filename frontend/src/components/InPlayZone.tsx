/**
 * InPlayZone Component
 * Displays cards that are in play for a player
 * 
 * Supports direct card interaction for tussles and activated abilities.
 * Cards that have available actions show a subtle glow when hovered.
 */

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardDisplay } from './CardDisplay';
import { cardGridTemplateColumns } from '../utils/cardGridTracks';
import { useReducedMotion } from '../hooks/useReducedMotion';
import type { Card } from '../types/game';

// How long the arrival ring stays mounted (matches the animation duration
// below). Kept as a constant so the timeout and the framer transition can't
// drift apart.
const ARRIVAL_DURATION_MS = 800;

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
  const prefersReducedMotion = useReducedMotion();

  // Track newly-arrived card IDs: present now but not in the previous
  // render's set. Skip on first mount so a mid-game board doesn't flash
  // every card that happens to already be in play.
  const previousIdsRef = useRef<Set<string> | null>(null);
  const [arrivedIds, setArrivedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const currentIds = new Set(cardList.map((c) => c.id));

    if (previousIdsRef.current === null) {
      // First render — establish the baseline, no arrivals.
      previousIdsRef.current = currentIds;
      return;
    }

    const previousIds = previousIdsRef.current;
    const newlyArrived = new Set<string>();
    currentIds.forEach((id) => {
      if (!previousIds.has(id)) newlyArrived.add(id);
    });
    previousIdsRef.current = currentIds;

    if (prefersReducedMotion || newlyArrived.size === 0) return;

    setArrivedIds(newlyArrived);
    const timer = setTimeout(() => setArrivedIds(new Set()), ARRIVAL_DURATION_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cardList.map((c) => c.id).join(','), prefersReducedMotion]);

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
              
              const isArriving = arrivedIds.has(card.id);

              return (
                <div key={card.id} style={{ position: 'relative' }}>
                  <CardDisplay
                    card={card}
                    size={size}
                    fluid={true}
                    isSelected={selectedCard === card.id}
                    isClickable={isClickable}
                    isHighlighted={isActionable}
                    onClick={isClickable ? () => onCardClick(card.id) : undefined}
                    enableLayoutAnimation={enableLayoutAnimation}
                  />
                  {/* Arrival emphasis: a card newly present in this zone (vs. the
                      previous render) gets a brief gold ring so it reads as "just
                      entered play" during opponent-turn polling, instead of just
                      popping in silently. Overlay only — no layout impact, no
                      pointer interception (§ arrival emphasis). */}
                  <AnimatePresence>
                    {isArriving && (
                      <motion.div
                        key="arrival-flash"
                        data-testid="arrival-flash"
                        style={{
                          position: 'absolute',
                          inset: 0,
                          borderRadius: '8px',
                          border: '2px solid var(--gold)',
                          pointerEvents: 'none',
                        }}
                        initial={{ opacity: 0.9, scale: 1.04 }}
                        animate={{ opacity: 0, scale: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: ARRIVAL_DURATION_MS / 1000 }}
                      />
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
      )}
    </div>
  );
}

/**
 * CardDisplay — a single card in the Paper & Ink language.
 *
 * Anatomy (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md §4): paper (yours) or ink
 * (theirs) face bound to card.owner via the material helper; identity crayon from
 * primary_color drives the frame border, corner brackets, cost box and stat-box
 * borders (no rules meaning — §2). Gochi-Hand name, left stat rail for Toys,
 * muted effect text, ready ⚡ bolt when a Toy can act, target pill on hand cards.
 * States per §6: playable glow, selected gold outline + ✓, broken grayscale +
 * stamp, disabled opacity. Exact values were read from the signed-off mockup
 * (docs/plans/wireframes/direction-boards.readable.html) and verified in the
 * /design.html harness.
 *
 * Framer Motion drives zone-transition layout + entrance; reduced motion honored.
 */

import { motion } from 'framer-motion';
import { useState } from 'react';
import type { Card } from '../types/game';
import { AnimatedStat } from './AnimatedStat';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { useResponsive } from '../hooks/useResponsive';
import { CardDetailModal } from './CardDetailModal';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { crayonForColor, costNumeralColor, materialFor } from '../theme/crayon';

interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
  isClickable?: boolean;
  isHighlighted?: boolean;
  isDisabled?: boolean;
  isUnplayable?: boolean;  // Card cannot be played this turn (not enough Charge, restricted, etc.)
  isTussling?: boolean;
  isCopy?: boolean;  // Card created by Copy effect (belongs to the copier — §1)
  size?: 'small' | 'medium' | 'large';
  /** Fill the parent grid track (up to a per-size max) instead of a fixed
   *  width. Use inside auto-fill grid containers so card names get the
   *  available space instead of truncating at the fixed width. */
  fluid?: boolean;
  /** Enable layout animations for zone transitions (uses card.id as layoutId) */
  enableLayoutAnimation?: boolean;
  /** Disable the mobile detail modal (e.g. when shown inside the modal itself) */
  disableDetailModal?: boolean;
  /** Which side this card's effect can currently target (hand cards only).
   *  Surfaces self-targetable effects before the target modal opens (WP-2 #5). */
  targetHint?: 'yours' | 'theirs' | 'either';
}

// Size configs. width is the fixed (and fluid-minimum) size; maxWidth caps
// fluid growth. Height is content-driven above a minimum so rows of cards in a
// grid-auto-rows:1fr container stay even without wasting space (no card art).
const SIZE = {
  small: { width: 120, maxWidth: 175, minHeight: 92, padding: '6px 7px', cost: 16, costFont: 10, name: 13, effect: 10.5, statSize: 'small' as const, showEffect: false, gap: 6 },
  medium: { width: 165, maxWidth: 250, minHeight: 104, padding: '7px 8px', cost: 20, costFont: 12, name: 16, effect: 10.5, statSize: 'medium' as const, showEffect: true, gap: 8 },
  large: { width: 330, maxWidth: 330, minHeight: 300, padding: '16px', cost: 30, costFont: 18, name: 26, effect: 13, statSize: 'large' as const, showEffect: true, gap: 12 },
};

// Target-pill palette (§4). Hand cards are always yours (paper), so these are
// the on-cream tints from the mockup; blue = your side, purple = their side.
const PILL = {
  yours: { background: '#E2E9DE', color: '#3D6CA8', label: 'your side' },
  theirs: { background: '#EBE2EE', color: '#7A4F9C', label: 'their side' },
  either: { background: 'linear-gradient(90deg,#E2E9DE,#EBE2EE)', color: '#6D5A9C', label: 'either side' },
};

export function CardDisplay({
  card,
  onClick,
  isSelected = false,
  isClickable = false,
  isHighlighted = false,
  isDisabled = false,
  isUnplayable = false,
  isTussling = false,
  isCopy = false,
  size = 'medium',
  fluid = false,
  enableLayoutAnimation = false,
  disableDetailModal = false,
  targetHint,
}: CardDisplayProps) {
  const prefersReducedMotion = useReducedMotion();
  const { isMobile } = useResponsive();
  const localPlayerId = useLocalPlayerId();
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);

  const effectivelyDisabled = isDisabled || isUnplayable;
  const isToy = card.card_type === 'Toy';
  const cfg = SIZE[size];

  // Ownership material (§1/§4): cream paper if you own it, dark ink otherwise.
  // Outside a game (no provider) default to own — sensible for card galleries.
  const isOwn = localPlayerId == null ? true : card.owner === localPlayerId;
  const material = materialFor(isOwn);
  const crayon = crayonForColor(card.primary_color);

  // A Toy in play that can act this turn shows the ready bolt; playable cards
  // (yours only) get the gold glow. Nothing glows on the opponent's turn (§6).
  const canAct = isHighlighted && isToy && !effectivelyDisabled;
  const isPlayable = isOwn && !effectivelyDisabled && (isHighlighted || isClickable);

  // Cost (effective when modified; ring signals cheaper=gold / costlier=danger).
  const displayCost = card.effective_cost ?? card.cost;
  const isCostModified = card.effective_cost != null && card.effective_cost !== card.cost;
  const costRing = isCostModified ? (card.effective_cost! < card.cost ? 'var(--gold)' : 'var(--danger)') : undefined;

  // Shadow: paper sits on the desk (drop shadow); ink is part of the board (none).
  // Playable adds the gold glow in front of the base shadow.
  const baseShadow = isOwn ? '0 3px 0 rgba(0,0,0,.4)' : 'none';
  const boxShadow = isPlayable
    ? `0 4px 10px rgba(242,193,78,.25)${isOwn ? ',0 3px 0 rgba(0,0,0,.4)' : ''}`
    : baseShadow;

  const shouldEnableMobileDetail = isMobile && !disableDetailModal;

  const handleInteraction = () => {
    if (shouldEnableMobileDetail) setIsDetailOpen(true);
    else if (isClickable && !effectivelyDisabled && onClick) onClick();
  };
  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
  };
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStart || !shouldEnableMobileDetail) { setTouchStart(null); return; }
    const touch = e.changedTouches[0];
    const deltaX = Math.abs(touch.clientX - touchStart.x);
    const deltaY = Math.abs(touch.clientY - touchStart.y);
    if (deltaX < 10 && deltaY < 10) setIsDetailOpen(true);
    setTouchStart(null);
  };
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && (shouldEnableMobileDetail || (isClickable && !effectivelyDisabled && onClick))) {
      e.preventDefault();
      handleInteraction();
    }
  };

  const interactive = shouldEnableMobileDetail || (isClickable && !effectivelyDisabled);
  const bracket = (corner: 'tl' | 'br') => (
    <div
      style={{
        position: 'absolute',
        width: '9px',
        height: '9px',
        ...(corner === 'tl'
          ? { top: '3px', left: '3px', borderTop: `2px solid ${crayon}`, borderLeft: `2px solid ${crayon}` }
          : { bottom: '3px', right: '3px', borderBottom: `2px solid ${crayon}`, borderRight: `2px solid ${crayon}` }),
      }}
    />
  );

  return (
    <>
      <motion.div
        layoutId={enableLayoutAnimation ? `card-${card.id}` : undefined}
        onClick={shouldEnableMobileDetail ? handleInteraction : (isClickable && !effectivelyDisabled ? onClick : undefined)}
        onTouchStart={shouldEnableMobileDetail ? handleTouchStart : undefined}
        onTouchEnd={shouldEnableMobileDetail ? handleTouchEnd : undefined}
        onKeyDown={handleKeyDown}
        tabIndex={interactive ? 0 : undefined}
        role={interactive ? 'button' : undefined}
        aria-label={shouldEnableMobileDetail || isClickable ? `${card.name} card` : undefined}
        className={interactive ? 'cursor-pointer' : effectivelyDisabled ? 'cursor-not-allowed' : ''}
        style={{
          width: fluid ? '100%' : `${cfg.width}px`,
          maxWidth: fluid ? `${cfg.maxWidth}px` : undefined,
          minHeight: `${cfg.minHeight}px`,
          padding: cfg.padding,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: material.surface,
          color: material.text,
          border: `2.5px solid ${crayon}`,
          borderRadius: '6px',
          boxShadow,
          outline: isSelected ? '3px solid var(--gold)' : undefined,
          outlineOffset: isSelected ? '2px' : undefined,
          filter: card.is_broken ? 'grayscale(35%)' : undefined,
        }}
        initial={enableLayoutAnimation ? false : { opacity: 0, scale: prefersReducedMotion ? 1 : 0.9 }}
        animate={{ opacity: effectivelyDisabled ? 0.5 : 1, scale: 1, x: isTussling && !prefersReducedMotion ? [0, -4, 4, -4, 4, 0] : 0 }}
        transition={{
          duration: prefersReducedMotion ? 0.1 : 0.3,
          x: { duration: 0.3, repeat: isTussling ? Infinity : 0 },
          layout: { duration: prefersReducedMotion ? 0.1 : 0.4, ease: 'easeInOut' },
        }}
        // Don't grow a selected card on hover: the scale pushes its gold outline
        // (offset 2px) past the card's bounds, and it's already chosen anyway.
        whileHover={interactive && !isSelected && !prefersReducedMotion ? { scale: 1.05 } : undefined}
        whileTap={interactive && !isSelected && !prefersReducedMotion ? { scale: 0.98 } : undefined}
      >
        {bracket('tl')}
        {bracket('br')}

        {/* Selected ✓ badge (targeting) — sits proud of the top-right corner. */}
        {isSelected && (
          <div
            style={{
              position: 'absolute', top: '-9px', right: '-9px', width: '20px', height: '20px',
              background: 'var(--gold)', color: 'var(--desk-bottom)', borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '11px', zIndex: 3,
            }}
          >
            ✓
          </div>
        )}

        {/* Header: cost box · name · ready bolt */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '5px' }}>
          <div
            title={isCostModified ? `Base cost: ${card.cost}` : undefined}
            style={{
              width: `${cfg.cost}px`, height: `${cfg.cost}px`, flexShrink: 0,
              background: crayon, color: costNumeralColor(crayon, isOwn), borderRadius: '3px',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: `${cfg.costFont}px`,
              outline: costRing ? `2px solid ${costRing}` : undefined, outlineOffset: '1px',
            }}
          >
            {displayCost}
          </div>
          <div
            style={{
              flex: 1, minWidth: 0, fontFamily: 'var(--font-card-name)', fontSize: `${cfg.name}px`,
              lineHeight: 1.05, overflow: 'hidden', display: '-webkit-box', WebkitBoxOrient: 'vertical',
              WebkitLineClamp: 2, overflowWrap: 'anywhere',
            }}
          >
            {card.name}
            {isCopy && (
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '8px', fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: material.textFaint, marginLeft: '5px' }}>
                copy
              </span>
            )}
          </div>
          {canAct ? (
            <div style={{ marginLeft: 'auto', fontSize: '11px', lineHeight: 1 }} title="Ready to act">⚡</div>
          ) : card.is_broken ? (
            // Cracked-card pip (the broken motif, §8) instead of the word — keeps
            // the header short so the name isn't squeezed, and never covers the
            // body so the effect text stays readable.
            <span
              title="Broken"
              aria-label="Broken"
              style={{
                marginLeft: 'auto', flexShrink: 0, alignSelf: 'flex-start',
                width: '11px', height: '15px', borderRadius: '2px',
                border: `1.5px solid ${material.danger}`,
                background: `linear-gradient(45deg, transparent 44%, ${material.danger} 44%, ${material.danger} 56%, transparent 56%)`,
              }}
            />
          ) : null}
        </div>

        {/* Body: Toy → stat rail + effect; Action → effect full width */}
        {isToy ? (
          <div style={{ display: 'flex', gap: `${cfg.gap}px` }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', flexShrink: 0 }}>
              {([['SPD', card.speed, card.base_speed, undefined], ['STR', card.strength, card.base_strength, undefined], ['STA', card.stamina, card.base_stamina, card.current_stamina]] as const).map(
                ([label, value, base, current]) => (
                  <AnimatedStat
                    key={label}
                    label={label}
                    value={value}
                    baseValue={base}
                    currentValue={current}
                    size={cfg.statSize}
                    crayonColor={crayon}
                    labelColor={material.textFaint}
                    valueColor={material.text}
                    buffedColor={material.buffed}
                    damagedColor={material.danger}
                  />
                )
              )}
            </div>
            {cfg.showEffect && card.effect_text && (
              <div style={{ fontSize: `${cfg.effect}px`, lineHeight: 1.35, color: material.textMuted, paddingTop: '2px' }}>
                {card.effect_text}
              </div>
            )}
          </div>
        ) : (
          cfg.showEffect && card.effect_text && (
            <div style={{ fontSize: `${cfg.effect}px`, lineHeight: 1.35, color: material.textMuted }}>
              {card.effect_text}
            </div>
          )
        )}

        {/* Target-side hint pill (hand cards). "either" is the case players miss
            (WP-2 #5). Pushed to the card's bottom edge. */}
        {targetHint && (
          <div style={{ marginTop: 'auto', paddingTop: '5px' }}>
            <span
              style={{
                display: 'inline-block', background: PILL[targetHint].background, color: PILL[targetHint].color,
                fontSize: '9px', fontWeight: 700, borderRadius: '999px', padding: '1px 7px', whiteSpace: 'nowrap',
              }}
            >
              🎯 {PILL[targetHint].label}
            </span>
          </div>
        )}

      </motion.div>

      {shouldEnableMobileDetail && (
        <CardDetailModal
          card={card}
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          onAction={isClickable && !effectivelyDisabled ? onClick : undefined}
          actionLabel="Select"
        />
      )}
    </>
  );
}

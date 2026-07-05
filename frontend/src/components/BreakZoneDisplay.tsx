/**
 * BreakZoneDisplay — the slim break slat (Paper & Ink §7.3).
 *
 * One quiet dashed slot per player: BREAK label · count badge · a row of
 * compact name chips (newest first, capped at 4 + "+n") · a "view" affordance
 * that opens the full pile. The count also lives in the score chip's broken
 * pip (§7.1) — repeating it here in bold is deliberate: the slat is the place
 * players look when reconstructing what just broke, and a bare name doesn't
 * answer "how many."
 *
 * Values from the signed-off mockup (6a break row).
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardDisplay } from './CardDisplay';
import { Modal } from './ui/Modal';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';
import type { Card } from '../types/game';

interface BreakZoneDisplayProps {
  cards: Card[];
  playerName: string;
}

// Decks are 6 cards — more than 4 broken at once is rare, but cap the row so
// it never wraps or pushes the slat wide.
const MAX_VISIBLE_CHIPS = 4;

const SLOT_STYLE: React.CSSProperties = {
  background: 'rgba(239,231,214,.05)',
  border: '1.5px dashed rgba(239,231,214,.2)',
  borderRadius: '6px',
  padding: '5px 8px',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  minWidth: 0,
  position: 'relative',
  overflow: 'hidden',
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: '9px',
  fontWeight: 900,
  letterSpacing: '.08em',
  color: 'rgba(237,232,222,.4)',
  flexShrink: 0,
};

const COUNT_BADGE_STYLE: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 900,
  color: 'rgba(237,232,222,.75)',
  flexShrink: 0,
};

// Chips shrink and ellipsize on narrow boards (390px) instead of hard-clipping
// mid-chip; minWidth keeps a few legible characters per chip.
const CHIP_STYLE: React.CSSProperties = {
  fontFamily: 'var(--font-card-name)',
  fontSize: '11px',
  color: 'rgba(237,232,222,.75)',
  background: 'rgba(237,232,222,.1)',
  border: '1px solid rgba(237,232,222,.18)',
  borderRadius: '4px',
  padding: '1px 6px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  flexShrink: 1,
  minWidth: '32px',
  maxWidth: '90px',
};

// The overflow chip never shrinks — it's the only signal that cards are
// hidden, needed most exactly when the row is tightest. It renders outside
// the shrinking chips container so it can't be clipped by its overflow.
const MORE_CHIP_STYLE: React.CSSProperties = {
  ...CHIP_STYLE,
  color: 'rgba(237,232,222,.45)',
  flexShrink: 0,
  minWidth: 0,
  maxWidth: 'none',
};

export function BreakZoneDisplay({ cards, playerName }: BreakZoneDisplayProps) {
  const cardList = cards || [];
  const [isListOpen, setIsListOpen] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const previousCount = usePreviousValue(cardList.length);

  const [flashType, setFlashType] = useState<'increase' | 'decrease' | null>(null);

  const countIncreased = previousCount !== undefined && cardList.length > previousCount;
  const countDecreased = previousCount !== undefined && cardList.length < previousCount;

  useEffect(() => {
    if (prefersReducedMotion) return;
    if (countIncreased) {
      setFlashType('increase');
      const timer = setTimeout(() => setFlashType(null), 500);
      return () => clearTimeout(timer);
    } else if (countDecreased) {
      setFlashType('decrease');
      const timer = setTimeout(() => setFlashType(null), 500);
      return () => clearTimeout(timer);
    }
  }, [countIncreased, countDecreased, prefersReducedMotion]);

  // Newest break first — the card players look for when reconstructing what
  // just happened.
  const newestFirst = [...cardList].reverse();
  const visibleChips = newestFirst.slice(0, MAX_VISIBLE_CHIPS);
  const overflowCount = cardList.length - visibleChips.length;

  if (cardList.length === 0) {
    return (
      <div style={SLOT_STYLE}>
        <span style={LABEL_STYLE}>BREAK</span>
        <span style={{ fontSize: '11px', fontStyle: 'italic', color: 'rgba(237,232,222,.28)' }}>empty</span>
      </div>
    );
  }

  return (
    <>
      {/* The whole slat is the click target (not just the tiny "view" label) —
          it's a small, non-obvious tap otherwise. */}
      <div
        onClick={() => setIsListOpen(true)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsListOpen(true); } }}
        role="button"
        tabIndex={0}
        aria-label={`View ${cardList.length} broken card${cardList.length > 1 ? 's' : ''} for ${playerName}`}
        style={{ ...SLOT_STYLE, cursor: 'pointer' }}
      >
        <span style={LABEL_STYLE}>BREAK</span>
        <span style={COUNT_BADGE_STYLE}>{cardList.length}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', overflow: 'hidden', minWidth: 0, flex: '1 1 auto' }}>
          {visibleChips.map((card) => (
            <span key={card.id} style={CHIP_STYLE}>{card.name}</span>
          ))}
        </div>
        {overflowCount > 0 && <span style={MORE_CHIP_STYLE}>+{overflowCount}</span>}
        <span style={{ marginLeft: 'auto', fontSize: '9px', color: 'rgba(237,232,222,.4)', flexShrink: 0 }} aria-hidden="true">
          view
        </span>

        {/* Transient change flash — gold down (fixed, good) / danger up (broke,
            bad), on-palette (§2). Mirrors AnimatedStat's pattern. */}
        <AnimatePresence>
          {flashType === 'increase' && (
            <motion.div
              key="flash-increase"
              style={{ position: 'absolute', inset: 0, borderRadius: '6px', pointerEvents: 'none', backgroundColor: 'var(--danger)' }}
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
            />
          )}
          {flashType === 'decrease' && (
            <motion.div
              key="flash-decrease"
              style={{ position: 'absolute', inset: 0, borderRadius: '6px', pointerEvents: 'none', backgroundColor: 'var(--gold)' }}
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
            />
          )}
        </AnimatePresence>
      </div>

      <Modal isOpen={isListOpen} onClose={() => setIsListOpen(false)} title={`${playerName} break zone`}>
        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
          <h3 className="font-bold text-lg">{playerName} · Break Zone ({cardList.length})</h3>
          <button
            onClick={() => setIsListOpen(false)}
            className="text-xl font-bold rounded hover:opacity-80"
            style={{ color: 'var(--ink-muted)', padding: '0 var(--spacing-component-xs)' }}
            aria-label="Close break zone list"
          >
            ✕
          </button>
        </div>
        {/* Medium cards so the effect text is readable — you need to know what
            a broken card does to decide whether to fix it. */}
        <div
          className="flex-1 min-h-0 overflow-y-auto content-start"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(var(--spacing-card-medium-min-w), 100%), 1fr))',
            gap: 'var(--spacing-component-sm)',
          }}
        >
          {newestFirst.map((card) => (
            <CardDisplay key={card.id} card={card} size="medium" fluid={true} disableDetailModal={true} />
          ))}
        </div>
      </Modal>
    </>
  );
}

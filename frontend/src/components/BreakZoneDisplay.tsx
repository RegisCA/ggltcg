/**
 * BreakZoneDisplay — the slim break slat (Paper & Ink §7.3).
 *
 * One quiet dashed slot per player: BREAK label · latest broken card's name
 * (Gochi) · `+n` when stacked · a "view" affordance that opens the full pile.
 * The count lives in the score chip's broken pip (§7.1), so the zone stays
 * deliberately quiet — no more full cards stacked in a tall panel.
 *
 * Values from the signed-off mockup (6a break row).
 */

import { useState } from 'react';
import { CardDisplay } from './CardDisplay';
import { Modal } from './ui/Modal';
import type { Card } from '../types/game';

interface BreakZoneDisplayProps {
  cards: Card[];
  playerName: string;
}

const SLOT_STYLE: React.CSSProperties = {
  background: 'rgba(239,231,214,.05)',
  border: '1.5px dashed rgba(239,231,214,.2)',
  borderRadius: '6px',
  padding: '5px 8px',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  minWidth: 0,
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: '9px',
  fontWeight: 900,
  letterSpacing: '.08em',
  color: 'rgba(237,232,222,.4)',
  flexShrink: 0,
};

export function BreakZoneDisplay({ cards, playerName }: BreakZoneDisplayProps) {
  const cardList = cards || [];
  const [isListOpen, setIsListOpen] = useState(false);

  // Newest break first — the card players look for when reconstructing what
  // just happened.
  const newestFirst = [...cardList].reverse();
  const newest = newestFirst[0];
  const hidden = cardList.length - 1;

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
      <div style={SLOT_STYLE}>
        <span style={LABEL_STYLE}>BREAK</span>
        <span
          style={{
            fontFamily: 'var(--font-card-name)',
            fontSize: '13px',
            color: 'rgba(237,232,222,.75)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            minWidth: 0,
          }}
        >
          {newest.name}
          {hidden > 0 && <span style={{ color: 'rgba(237,232,222,.45)' }}> +{hidden}</span>}
        </span>
        <button
          onClick={() => setIsListOpen(true)}
          style={{ marginLeft: 'auto', fontSize: '9px', color: 'rgba(237,232,222,.4)', background: 'none', border: 'none', cursor: 'pointer', flexShrink: 0, padding: '2px 4px' }}
          aria-label={`View all ${cardList.length} broken card${cardList.length > 1 ? 's' : ''} for ${playerName}`}
        >
          view
        </button>
      </div>

      <Modal isOpen={isListOpen} onClose={() => setIsListOpen(false)} title={`${playerName} break zone`}>
        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
          <h3 className="font-bold text-lg">{playerName} · Break Zone ({cardList.length})</h3>
          <button
            onClick={() => setIsListOpen(false)}
            className="text-gray-400 hover:text-white text-xl font-bold rounded"
            style={{ padding: '0 var(--spacing-component-xs)' }}
            aria-label="Close break zone list"
          >
            ✕
          </button>
        </div>
        <div
          className="flex-1 min-h-0 overflow-y-auto content-start"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(var(--spacing-card-small-w), 100%), 1fr))',
            gap: 'var(--spacing-component-sm)',
          }}
        >
          {newestFirst.map((card) => (
            <CardDisplay key={card.id} card={card} size="small" fluid={true} disableDetailModal={true} />
          ))}
        </div>
      </Modal>
    </>
  );
}

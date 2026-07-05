/**
 * CardDetailModal Component
 * Mobile-optimized modal for displaying card details with full readability.
 * Opened by CardDisplay's mobile tap-to-read affordance — LIVE and load-bearing
 * on mobile (see CardDisplay.tsx `shouldEnableMobileDetail`); this restyle only
 * changes appearance, never when/whether it opens.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md §4): the
 * enlarged card reuses the same crayon identity + ownership material as the
 * real board card (`crayonForColor`, `materialFor` via `useLocalPlayerId` —
 * see CardDisplay.tsx) so it reads as the same object at a bigger size, inside
 * the settled dark-panel + gold-hairline modal chrome (Leaderboard/PlayerStats
 * idiom) for backdrop, close button, and Esc/backdrop-click dismissal.
 *
 * Keeps its job: large readable effect text (>=16px), labeled stats, >=44px
 * touch targets, optional action button.
 */

import { Modal } from './ui/Modal';
import type { Card } from '../types/game';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { crayonForColor, costNumeralColor, materialFor } from '../theme/crayon';

interface CardDetailModalProps {
  card: Card;
  isOpen: boolean;
  onClose: () => void;
  onAction?: () => void;
  actionLabel?: string;
}

export function CardDetailModal({
  card,
  isOpen,
  onClose,
  onAction,
  actionLabel = 'Select',
}: CardDetailModalProps) {
  const localPlayerId = useLocalPlayerId();
  const isToy = card.card_type === 'Toy';

  const isOwn = localPlayerId == null ? true : card.owner === localPlayerId;
  const material = materialFor(isOwn);
  const crayon = crayonForColor(card.primary_color);

  const displayCost = card.effective_cost ?? card.cost;
  const isCostModified = card.effective_cost != null && card.effective_cost !== card.cost;
  const costRing = isCostModified ? (card.effective_cost! < card.cost ? 'var(--gold)' : 'var(--danger)') : undefined;

  const handleAction = () => {
    if (onAction) {
      onAction();
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${card.name} Details`}
      closeOnBackdropClick={true}
      closeOnEscape={true}
      panelStyle={{
        width: '420px',
        maxWidth: '100%',
        maxHeight: '90vh',
        background: '#241E17',
        borderRadius: '8px',
        border: '1px solid var(--gold)',
        boxShadow: '0 8px 24px rgba(0,0,0,.4)',
        padding: 0,
      }}
    >
      <div className="flex flex-col" style={{ maxHeight: '90vh' }}>
        {/* Panel header (settled idiom): close affordance */}
        <div
          className="flex-shrink-0 flex justify-end"
          style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-sm) 0' }}
        >
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              minWidth: 'var(--size-touch-target-min)',
              minHeight: 'var(--size-touch-target-min)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '22px',
              fontWeight: 900,
              color: 'var(--ink-faint)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            &times;
          </button>
        </div>

        {/* The enlarged card itself, in the card's own crayon + material */}
        <div
          className="overflow-y-auto"
          style={{
            margin: '0 var(--spacing-component-lg) var(--spacing-component-lg)',
            padding: 'var(--spacing-component-lg)',
            background: material.surface,
            color: material.text,
            border: `3px solid ${crayon}`,
            borderRadius: '10px',
            boxShadow: isOwn ? '0 3px 0 rgba(0,0,0,.4)' : 'none',
          }}
        >
          {/* Header: cost chip + name */}
          <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)', marginBottom: 'var(--spacing-component-md)' }}>
            <div
              title={isCostModified ? `Base cost: ${card.cost}` : undefined}
              className="flex items-center justify-center flex-shrink-0"
              style={{
                width: 'var(--size-touch-target-lg)',
                height: 'var(--size-touch-target-lg)',
                background: crayon,
                color: costNumeralColor(crayon, isOwn),
                borderRadius: '6px',
                fontWeight: 900,
                fontSize: 'var(--font-size-mobile-detail-title)',
                outline: costRing ? `2px solid ${costRing}` : undefined,
                outlineOffset: '2px',
              }}
            >
              {displayCost}
            </div>
            <h2
              style={{
                fontFamily: 'var(--font-card-name)',
                fontSize: 'var(--font-size-mobile-detail-title)',
                lineHeight: '1.15',
                flex: 1,
                minWidth: 0,
                overflowWrap: 'anywhere',
              }}
            >
              {card.name}
            </h2>
          </div>

          {/* Broken badge */}
          {card.is_broken && (
            <div className="flex flex-wrap" style={{ gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)' }}>
              <span
                className="font-bold"
                style={{
                  borderRadius: '4px',
                  color: material.danger,
                  border: `1.5px solid ${material.danger}`,
                  fontSize: 'var(--font-size-lg)',
                  padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                }}
              >
                BROKEN
              </span>
            </div>
          )}

          {/* Toy Stats - Large and Readable */}
          {isToy && (
            <div style={{ marginBottom: 'var(--spacing-component-md)' }}>
              <h3
                className="font-bold"
                style={{
                  color: material.textFaint,
                  fontSize: 'var(--font-size-mobile-detail-heading)',
                  marginBottom: 'var(--spacing-component-sm)',
                }}
              >
                Stats
              </h3>
              <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
                {/* Speed */}
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                  <span style={{ color: material.textFaint, fontSize: 'var(--font-size-mobile-detail-label)', flexShrink: 0 }}>
                    Speed
                  </span>
                  <span
                    className="font-bold text-right"
                    style={{
                      fontSize: 'var(--font-size-2xl)',
                      color: card.speed !== card.base_speed ? material.buffed : material.text,
                    }}
                  >
                    {card.speed}
                    {card.speed !== card.base_speed && (
                      <span style={{ color: material.textFaint, fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
                        (Base: {card.base_speed})
                      </span>
                    )}
                  </span>
                </div>

                {/* Strength */}
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                  <span style={{ color: material.textFaint, fontSize: 'var(--font-size-mobile-detail-label)', flexShrink: 0 }}>
                    Strength
                  </span>
                  <span
                    className="font-bold text-right"
                    style={{
                      fontSize: 'var(--font-size-2xl)',
                      color: card.strength !== card.base_strength ? material.buffed : material.text,
                    }}
                  >
                    {card.strength}
                    {card.strength !== card.base_strength && (
                      <span style={{ color: material.textFaint, fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
                        (Base: {card.base_strength})
                      </span>
                    )}
                  </span>
                </div>

                {/* Stamina */}
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                  <span style={{ color: material.textFaint, fontSize: 'var(--font-size-mobile-detail-label)', flexShrink: 0 }}>
                    Stamina
                  </span>
                  <span
                    className="font-bold text-right"
                    style={{
                      fontSize: 'var(--font-size-2xl)',
                      color: (card.current_stamina ?? 0) < (card.stamina ?? 0)
                        ? material.danger // Damaged (current < max)
                        : card.stamina !== card.base_stamina
                        ? material.buffed // Buffed/debuffed (max != base)
                        : material.text, // Normal
                    }}
                  >
                    {card.current_stamina} / {card.stamina}
                    {card.stamina !== card.base_stamina && (
                      <span style={{ color: material.textFaint, fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
                        (Base: {card.base_stamina})
                      </span>
                    )}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Effect Text - Large and Readable */}
          {card.effect_text && (
            <div>
              <h3
                className="font-bold"
                style={{
                  color: material.textFaint,
                  fontSize: 'var(--font-size-mobile-detail-heading)',
                  marginBottom: 'var(--spacing-component-xs)',
                }}
              >
                Effect
              </h3>
              <p
                style={{
                  color: material.textMuted,
                  fontSize: 'var(--font-size-mobile-detail-text)',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {card.effect_text}
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons (outside the card face, part of panel chrome) */}
        <div
          className="flex-shrink-0 flex"
          style={{
            gap: 'var(--spacing-component-sm)',
            padding: '0 var(--spacing-component-lg) var(--spacing-component-lg)',
          }}
        >
          {onAction && (
            <button
              onClick={handleAction}
              className="flex-1 font-bold"
              style={{
                minHeight: 'var(--size-touch-target-button)',
                fontSize: 'var(--font-size-lg)',
                padding: 'var(--spacing-component-sm)',
                borderRadius: '6px',
                border: 'none',
                background: 'var(--gold)',
                color: 'var(--desk-bottom)',
                boxShadow: '0 3px 0 rgba(0,0,0,.5)',
                cursor: 'pointer',
              }}
            >
              {actionLabel}
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 font-bold"
            style={{
              minHeight: 'var(--size-touch-target-button)',
              fontSize: 'var(--font-size-lg)',
              padding: 'var(--spacing-component-sm)',
              borderRadius: '6px',
              border: 'none',
              background: 'rgba(237,232,222,.1)',
              color: 'var(--ink-text)',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}

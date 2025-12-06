/**
 * CardDetailModal Component
 * Mobile-optimized modal for displaying card details with full readability
 * 
 * Shows enlarged card with:
 * - Large readable effect text (≥16px)
 * - Clear stat displays with labels
 * - Proper touch targets (≥44×44px)
 * - Optional action button for selectable cards
 */

import { Modal } from './ui/Modal';
import type { Card } from '../types/game';

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
  const isToy = card.card_type === 'Toy';
  const accentColor = card.accent_color || (isToy ? '#C74444' : '#8B5FA8');

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
    >
      <div className="content-spacing max-h-[85vh] overflow-y-auto">
        {/* Header: Close Button */}
        <div className="flex justify-between items-start">
          <h2
            className="font-bold text-white"
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 'var(--font-size-mobile-detail-title)',
              lineHeight: '1.2',
            }}
          >
            {card.name}
          </h2>
          <button
            onClick={onClose}
            className="flex items-center justify-center bg-gray-700 hover:bg-gray-600 text-white font-bold rounded"
            style={{
              minWidth: 'var(--size-touch-target-min)',
              minHeight: 'var(--size-touch-target-min)',
              fontSize: 'var(--font-size-2xl)',
            }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Card Type and Cost */}
        <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
          <div
            className="flex items-center justify-center font-bold text-white rounded"
            style={{
              width: 'var(--size-touch-target-lg)',
              height: 'var(--size-touch-target-lg)',
              backgroundColor: accentColor,
              fontSize: 'var(--font-size-mobile-detail-title)',
              boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
            }}
          >
            {card.cost}
          </div>
          <div className="flex flex-col justify-center">
            <div
              className="text-gray-400"
              style={{ fontSize: 'var(--font-size-lg)' }}
            >
              Type
            </div>
            <div
              className="font-bold text-white rounded inline-block"
              style={{
                fontSize: 'var(--font-size-xl)',
                backgroundColor: isToy ? 'var(--ui-toy-badge)' : 'var(--ui-action-badge)',
                boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
              }}
            >
              {card.card_type}
            </div>
          </div>
        </div>

        {/* Badges (Copy, Sleeped) */}
        {card.is_sleeped && (
          <div className="flex flex-wrap" style={{ gap: 'var(--spacing-component-xs)' }}>
            <span
              className="rounded font-bold text-white bg-red-600"
              style={{
                fontSize: 'var(--font-size-lg)',
                padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
              }}
            >
              SLEEPED
            </span>
          </div>
        )}

        {/* Toy Stats - Large and Readable */}
        {isToy && (
          <div className="card-padding bg-gray-800 rounded">
            <h3
              className="text-gray-300 font-bold"
              style={{
                fontSize: 'var(--font-size-mobile-detail-heading)',
                marginBottom: 'var(--spacing-component-sm)',
              }}
            >
              Stats
            </h3>
            <div className="flex flex-col" style={{ gap: 'var(--spacing-component-sm)' }}>
              {/* Speed */}
              <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                <span className="text-gray-400 flex-shrink-0" style={{ fontSize: 'var(--font-size-mobile-detail-label)' }}>
                  ⚡ Speed
                </span>
                <span
                  className="font-bold text-right"
                  style={{
                    fontSize: 'var(--font-size-2xl)',
                    color: card.speed !== card.base_speed ? 'var(--color-stat-buffed)' : 'white',
                  }}
                >
                  {card.speed}
                  {card.speed !== card.base_speed && (
                    <span className="text-gray-400" style={{ fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
                      (Base: {card.base_speed})
                    </span>
                  )}
                </span>
              </div>

              {/* Strength */}
              <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                <span className="text-gray-400 flex-shrink-0" style={{ fontSize: 'var(--font-size-mobile-detail-label)' }}>
                  💪 Strength
                </span>
                <span
                  className="font-bold text-right"
                  style={{
                    fontSize: 'var(--font-size-2xl)',
                    color: card.strength !== card.base_strength ? 'var(--color-stat-buffed)' : 'white',
                  }}
                >
                  {card.strength}
                  {card.strength !== card.base_strength && (
                    <span className="text-gray-400" style={{ fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
                      (Base: {card.base_strength})
                    </span>
                  )}
                </span>
              </div>

              {/* Stamina */}
              <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
                <span className="text-gray-400 flex-shrink-0" style={{ fontSize: 'var(--font-size-mobile-detail-label)' }}>
                  ❤️ Stamina
                </span>
                <span
                  className="font-bold text-right"
                  style={{
                    fontSize: 'var(--font-size-2xl)',
                    color: (card.current_stamina ?? 0) < (card.stamina ?? 0)
                      ? 'var(--color-stat-damaged)' // Damaged (current < max)
                      : card.stamina !== card.base_stamina
                      ? 'var(--color-stat-buffed)' // Buffed/debuffed (max ≠ base)
                      : 'white', // Normal
                  }}
                >
                  {card.current_stamina} / {card.stamina}
                  {card.stamina !== card.base_stamina && (
                    <span className="text-gray-400" style={{ fontSize: 'var(--font-size-sm)', marginLeft: 'var(--spacing-component-xs)' }}>
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
          <div className="card-padding bg-gray-800 rounded">
            <h3
              className="text-gray-300 font-bold"
              style={{
                fontSize: 'var(--font-size-mobile-detail-heading)',
                marginBottom: 'var(--spacing-component-xs)',
              }}
            >
              Effect
            </h3>
            <p
              className="text-gray-300 italic"
              style={{
                fontSize: 'var(--font-size-mobile-detail-text)',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
              }}
            >
              {card.effect_text}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
          {onAction && (
            <button
              onClick={handleAction}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold rounded"
              style={{
                minHeight: 'var(--size-touch-target-button)',
                fontSize: 'var(--font-size-lg)',
                padding: 'var(--spacing-component-sm)',
              }}
            >
              {actionLabel}
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded"
            style={{
              minHeight: 'var(--size-touch-target-button)',
              fontSize: 'var(--font-size-lg)',
              padding: 'var(--spacing-component-sm)',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}

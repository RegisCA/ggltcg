/**
 * TargetSelectionModal Component
 * Modal for selecting targets when playing cards that require targeting
 * (Copy, Sun, Wake, Twist, etc.)
 * 
 * Refactored to use Modal component wrapper for consistent accessibility.
 */

import { useState, useEffect } from 'react';
import { Modal } from './ui/Modal';
import { CardDisplay } from './CardDisplay';
import type { Card, ValidAction } from '../types/game';

interface TargetSelectionModalProps {
  action: ValidAction;
  availableTargets: Card[];
  onConfirm: (selectedTargets: string[], alternativeCostCard?: string) => void;
  onCancel: () => void;
  alternativeCostOptions?: Card[]; // For Ballaber
}

export function TargetSelectionModal({
  action,
  availableTargets,
  onConfirm,
  onCancel,
  alternativeCostOptions,
}: TargetSelectionModalProps) {
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [useAlternativeCost, setUseAlternativeCost] = useState(false);
  const [alternativeCostCard, setAlternativeCostCard] = useState<string | null>(null);

  const maxTargets = action.max_targets || 1;
  const minTargets = action.min_targets || 1;
  // Filter alternative cost options: must be in Play or Hand zone, and not Ballaber itself
  const filteredAlternativeCostOptions = (alternativeCostOptions || []).filter(
    (card) => card.id !== action.card_id && (card.zone === 'Hand' || card.zone === 'InPlay')
  );
  // Show alternative cost UI if the card has alternative cost available (like Ballaber)
  // Even if there are no cards to sleep, we need to show "Pay CC" option
  const hasAlternativeCost = action.alternative_cost_available === true;
  const hasCardsToSleep = filteredAlternativeCostOptions.length > 0;

  // Reset state when action changes
  useEffect(() => {
    setSelectedTargets([]);
    setAlternativeCostCard(null);
    // If alternative cost is available but no cards to sleep, auto-select "Pay CC"
    if (hasAlternativeCost && !hasCardsToSleep) {
      setUseAlternativeCost(true);
    } else {
      setUseAlternativeCost(false);
    }
  }, [action.card_id, hasAlternativeCost, hasCardsToSleep]);

  const toggleTarget = (cardId: string) => {
    if (selectedTargets.includes(cardId)) {
      setSelectedTargets(selectedTargets.filter((id) => id !== cardId));
    } else if (selectedTargets.length < maxTargets) {
      setSelectedTargets([...selectedTargets, cardId]);
    }
  };

  // Only allow one card to be selected for alternative cost
  const selectAlternativeCostCard = (cardId: string) => {
    setAlternativeCostCard(cardId);
    setUseAlternativeCost(true);
    setSelectedTargets([]); // Clear normal targets if switching to alt cost
  };

  // Select to pay CC instead of sleeping a card
  const selectPayCC = () => {
    setUseAlternativeCost(true);
    setAlternativeCostCard(null);
    setSelectedTargets([]);
  };

  const handleConfirm = () => {
    // Ballaber: if using alt cost with card, must have selected a card
    if (useAlternativeCost && alternativeCostCard) {
      onConfirm([], alternativeCostCard);
      return;
    }
    // Ballaber: paying CC (useAlternativeCost=true but no card selected)
    if (useAlternativeCost && !alternativeCostCard) {
      onConfirm([], undefined);
      return;
    }
    // Normal targeting
    if (selectedTargets.length < minTargets && minTargets > 0) return;
    onConfirm(selectedTargets, undefined);
  };

  const canConfirm = () => {
    // Ballaber: if using alt cost, either have CC selected or a card selected
    if (useAlternativeCost) {
      return true; // Can confirm with just CC payment or with a card
    }
    // Normal targeting
    if (minTargets === 0) return true;
    return selectedTargets.length >= minTargets && selectedTargets.length <= maxTargets;
  };

  const modalTitle = action.action_type === 'tussle' 
    ? `Tussle with ${action.card_name}` 
    : `Playing ${action.card_name}`;

  return (
    <Modal
      isOpen={true}
      onClose={onCancel}
      title={modalTitle}
      closeOnBackdropClick={false}
      closeOnEscape={true}
    >
      <div className="flex flex-col" style={{ maxHeight: '70vh' }}>
        {/* Action Description */}
        <div className="flex-shrink-0" style={{ marginBottom: 'var(--spacing-component-md)' }}>
          {action.action_type !== 'tussle' && action.cost_cc !== undefined && (
            <p className="text-base text-gray-300" style={{ marginBottom: 'var(--spacing-component-xs)' }}>
              Cost: {action.cost_cc} CC
            </p>
          )}
          <p className="text-base text-gray-100" style={{ marginBottom: 'var(--spacing-component-md)' }}>
            {action.description}
          </p>
          <div className="flex" style={{ gap: 'var(--spacing-component-sm)' }}>
            <button
              onClick={onCancel}
              className="rounded-lg bg-gray-600 hover:bg-gray-700 font-bold transition-all text-white focus:ring-2 focus:ring-yellow-400"
              style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-xl)' }}
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canConfirm()}
              className={`
                rounded-lg font-bold transition-all text-white focus:ring-2 focus:ring-yellow-400
                ${canConfirm()
                  ? action.action_type === 'tussle' 
                    ? 'bg-red-600 hover:bg-red-700 cursor-pointer'
                    : 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                  : 'bg-gray-600 cursor-not-allowed opacity-50'
                }
              `}
              style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-xl)' }}
            >
              {action.action_type === 'tussle' ? 'Attack!' : 'Confirm'}
            </button>
          </div>
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          {/* Ballaber alternative cost: one-click selection */}
          {hasAlternativeCost && (
            <div style={{ marginBottom: 'var(--spacing-component-md)' }}>
              <h3 className="text-lg font-bold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Pay cost to play Ballaber:</h3>
              <button
                style={{
                  ...(useAlternativeCost && !alternativeCostCard
                    ? { boxShadow: '0 0 0 4px rgb(250 204 21), 0 10px 15px -3px rgba(250, 204, 21, 0.5)' }
                    : {}),
                  padding: 'var(--spacing-component-sm) var(--spacing-component-md)',
                  marginBottom: 'var(--spacing-component-md)'
                }}
                className={`
                  w-full rounded transition-all text-sm focus:ring-2 focus:ring-yellow-400
                  ${useAlternativeCost && !alternativeCostCard
                    ? 'bg-red-700'
                    : 'bg-red-600 hover:bg-red-700 cursor-pointer'
                  }
                `}
                onClick={selectPayCC}
              >
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <span className="font-medium leading-tight text-left flex-1">
                    Pay {action.cost_cc} CC
                  </span>
                  <span 
                    className="rounded text-xs font-bold whitespace-nowrap flex-shrink-0 bg-black bg-opacity-30"
                    style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-xs)' }}
                  >
                    {action.cost_cc} CC
                  </span>
                </div>
              </button>
              {hasCardsToSleep ? (
                <>
                  <h4 className="text-md font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Or select a card to sleep:</h4>
                  <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                    {filteredAlternativeCostOptions.map((card) => {
                      const isSelected = alternativeCostCard === card.id;
                      return (
                        <div
                          key={card.id}
                          onClick={() => selectAlternativeCostCard(card.id)}
                          className="flex justify-center"
                        >
                          <CardDisplay
                            card={card}
                            size="medium"
                            isSelected={isSelected}
                            isClickable={true}
                          />
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : (
                <p className="text-gray-400 text-sm">
                  No cards available to sleep. You must pay {action.cost_cc} CC.
                </p>
              )}
            </div>
          )}

          {/* Target Selection (for other cards) */}
          {!useAlternativeCost && availableTargets.length > 0 && (
            <div>
              <h3 className="text-lg font-bold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                {maxTargets > 1
                  ? `Select up to ${maxTargets} target${maxTargets !== 1 ? 's' : ''}`
                  : 'Select a target '
                }
                {minTargets === 0 && ' (optional)'}
                {selectedTargets.length > 0 && (
                  <span className="text-yellow-400" style={{ marginLeft: 'var(--spacing-component-xs)' }}>
                    ({selectedTargets.length}/{maxTargets} selected)
                  </span>
                )}
              </h3>
              <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-sm)' }}>
                {availableTargets.map((card) => {
                  const isSelected = selectedTargets.includes(card.id);
                  const isDisabled = !isSelected && selectedTargets.length >= maxTargets;
                  return (
                    <div
                      key={card.id}
                      onClick={() => !isDisabled && toggleTarget(card.id)}
                      className="flex justify-center"
                    >
                      <CardDisplay
                        card={card}
                        size="medium"
                        isSelected={isSelected}
                        isClickable={!isDisabled}
                        isDisabled={isDisabled}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!useAlternativeCost && availableTargets.length === 0 && minTargets === 0 && !hasAlternativeCost && (
            <div className="text-center text-gray-400">
              No targets available, but you can still play this card.
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

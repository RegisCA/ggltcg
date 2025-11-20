/**
 * TargetSelectionModal Component
 * Modal for selecting targets when playing cards that require targeting
 * (Copy, Sun, Wake, Twist, etc.)
 */

import { useState, useEffect } from 'react';
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
  const hasAlternativeCost = action.alternative_cost_available && filteredAlternativeCostOptions.length > 0;

  // Reset state when action changes
  useEffect(() => {
    setSelectedTargets([]);
    setUseAlternativeCost(false);
    setAlternativeCostCard(null);
  }, [action.card_id]);

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

  const handleConfirm = () => {
    // Ballaber: if using alt cost, must have selected a card
    if (useAlternativeCost) {
      if (!alternativeCostCard) return;
      onConfirm([], alternativeCostCard);
      return;
    }
    // Normal targeting
    if (selectedTargets.length < minTargets && minTargets > 0) return;
    onConfirm(selectedTargets, undefined);
  };

  const canConfirm = () => {
    // Ballaber: if using alt cost, must have selected a card
    if (useAlternativeCost) {
      return !!alternativeCostCard;
    }
    // Normal targeting
    if (minTargets === 0) return true;
    return selectedTargets.length >= minTargets && selectedTargets.length <= maxTargets;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-game-card rounded-lg border-2 border-game-highlight max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b-2 border-game-accent sticky top-0 bg-game-card">
          <h2 className="text-2xl font-bold mb-2">
            Playing {action.card_name}
          </h2>
          <p className="text-gray-300">
            {action.description}
          </p>
        </div>

        {/* Ballaber alternative cost: one-click selection */}
        {hasAlternativeCost && (
          <div className="p-4 bg-gray-900">
            <h3 className="text-lg font-bold mb-2">Pay cost to play Ballaber:</h3>
            <div className="flex gap-4 mb-4">
              <button
                className={`px-6 py-2 rounded font-bold transition-all ${!useAlternativeCost ? 'bg-game-highlight hover:bg-red-600 cursor-pointer' : 'bg-gray-600 opacity-50'}`}
                onClick={() => {
                  setUseAlternativeCost(false);
                  setAlternativeCostCard(null);
                }}
                disabled={useAlternativeCost}
              >
                Pay {action.cost_cc} CC
              </button>
            </div>
            <h4 className="text-md font-semibold mb-2">Or select a card to sleep:</h4>
            <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
              {filteredAlternativeCostOptions.map((card) => {
                const isSelected = alternativeCostCard === card.id;
                return (
                  <div
                    key={card.id}
                    onClick={() => selectAlternativeCostCard(card.id)}
                    style={{ display: 'flex', justifyContent: 'center' }}
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
          </div>
        )}

        {/* Target Selection (for other cards) */}
        {!useAlternativeCost && availableTargets.length > 0 && (
          <div className="p-4">
            <h3 className="text-lg font-bold mb-2">
              {maxTargets > 1
                ? `Select up to ${maxTargets} target${maxTargets !== 1 ? 's' : ''}`
                : 'Select a target'
              }
              {minTargets === 0 && ' (optional)'}
              {selectedTargets.length > 0 && (
                <span className="ml-2 text-game-highlight">
                  ({selectedTargets.length}/{maxTargets} selected)
                </span>
              )}
            </h3>
            <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
              {availableTargets.map((card) => {
                const isSelected = selectedTargets.includes(card.id);
                const isDisabled = !isSelected && selectedTargets.length >= maxTargets;
                return (
                  <div
                    key={card.id}
                    onClick={() => !isDisabled && toggleTarget(card.id)}
                    style={{ display: 'flex', justifyContent: 'center' }}
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
          <div className="p-4 text-center text-gray-400">
            No targets available, but you can still play this card.
          </div>
        )}

        {/* Footer with action buttons */}
        <div className="p-4 border-t-2 border-game-accent flex justify-end gap-3 sticky bottom-0 bg-game-card">
          <button
            onClick={onCancel}
            className="px-6 py-2 rounded bg-gray-600 hover:bg-gray-700 font-bold transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm()}
            className={`
              px-6 py-2 rounded font-bold transition-all
              ${canConfirm()
                ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                : 'bg-gray-600 cursor-not-allowed opacity-50'
              }
            `}
          >
            Confirm
            {useAlternativeCost && alternativeCostCard
              ? ' (Sleep card & play)'
              : selectedTargets.length > 0
              ? ` (${selectedTargets.length} target${selectedTargets.length !== 1 ? 's' : ''})`
              : ''
            }
          </button>
        </div>
      </div>
    </div>
  );
}

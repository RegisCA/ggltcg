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
  const hasAlternativeCost = action.alternative_cost_available && alternativeCostOptions && alternativeCostOptions.length > 0;

  // Reset state when action changes
  useEffect(() => {
    setSelectedTargets([]);
    setUseAlternativeCost(false);
    setAlternativeCostCard(null);
  }, [action.card_name]);

  const toggleTarget = (cardName: string) => {
    if (selectedTargets.includes(cardName)) {
      setSelectedTargets(selectedTargets.filter((name) => name !== cardName));
    } else if (selectedTargets.length < maxTargets) {
      setSelectedTargets([...selectedTargets, cardName]);
    }
  };

  const toggleAlternativeCostCard = (cardName: string) => {
    if (alternativeCostCard === cardName) {
      setAlternativeCostCard(null);
    } else {
      setAlternativeCostCard(cardName);
    }
  };

  const handleConfirm = () => {
    // Validate selection
    if (selectedTargets.length < minTargets && minTargets > 0) {
      return; // Don't allow confirmation if minimum not met
    }

    // For Ballaber alternative cost, ensure a card is selected
    if (useAlternativeCost && !alternativeCostCard) {
      return;
    }

    onConfirm(selectedTargets, useAlternativeCost ? alternativeCostCard || undefined : undefined);
  };

  const canConfirm = () => {
    // If using alternative cost, must have selected a card to sleep
    if (useAlternativeCost && !alternativeCostCard) {
      return false;
    }

    // Check target selection requirements
    if (minTargets === 0) {
      // Optional targeting - can confirm with 0 or more targets (up to max)
      return true;
    }

    // Required targeting - must meet minimum
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

          {/* Alternative Cost Option (Ballaber) */}
          {hasAlternativeCost && (
            <div className="mt-3 p-3 bg-gray-800 rounded">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useAlternativeCost}
                  onChange={(e) => setUseAlternativeCost(e.target.checked)}
                  className="w-5 h-5 cursor-pointer"
                />
                <span className="font-semibold">
                  Use alternative cost (sleep a card instead of paying {action.cost_cc} CC)
                </span>
              </label>
            </div>
          )}
        </div>

        {/* Alternative Cost Selection */}
        {useAlternativeCost && alternativeCostOptions && (
          <div className="p-4 bg-gray-900">
            <h3 className="text-lg font-bold mb-2">
              Select a card to sleep (alternative payment):
            </h3>
            <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
              {alternativeCostOptions.map((card) => {
                const isSelected = alternativeCostCard === card.name;
                
                return (
                  <div
                    key={card.name}
                    onClick={() => toggleAlternativeCostCard(card.name)}
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

        {/* Target Selection */}
        {availableTargets.length > 0 && (
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
                const isSelected = selectedTargets.includes(card.name);
                const isDisabled = !isSelected && selectedTargets.length >= maxTargets;
                
                return (
                  <div
                    key={card.name}
                    onClick={() => !isDisabled && toggleTarget(card.name)}
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

        {availableTargets.length === 0 && minTargets === 0 && !hasAlternativeCost && (
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

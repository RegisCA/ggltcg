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
    <div 
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.80)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem'
      }}
    >
      <div 
        className="bg-gray-900 rounded-xl border-4 border-game-highlight shadow-2xl flex flex-col" 
        style={{ 
          width: '700px',
          maxHeight: '80vh',
        }}
      >
        {/* Header */}
        <div className="p-4 border-b-4 border-game-accent bg-gray-800 flex-shrink-0">
          <h2 className="text-2xl font-bold mb-1 text-game-highlight">
            Playing {action.card_name}
          </h2>
          <p className="text-base text-gray-300 mb-3">
            Cost: {action.cost_cc} CC
          </p>
          <p className="text-base text-gray-100 mb-3">
            {action.description}
          </p>
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="px-8 py-3 rounded-lg bg-gray-600 hover:bg-gray-700 font-bold transition-all text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canConfirm()}
              className={`
                px-8 py-3 rounded-lg font-bold transition-all text-white
                ${canConfirm()
                  ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                  : 'bg-gray-600 cursor-not-allowed opacity-50'
                }
              `}
            >
              Confirm
              {useAlternativeCost && alternativeCostCard
                ? ' (Sleep card)'
                : selectedTargets.length > 0
                ? ` (${selectedTargets.length})`
                : ''
              }
            </button>
          </div>
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
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
        </div>
      </div>
    </div>
  );
}

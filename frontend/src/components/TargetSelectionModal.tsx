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
            </button>
          </div>
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          {/* Ballaber alternative cost: one-click selection */}
          {hasAlternativeCost && (
            <div className="p-4 bg-gray-900">
              <h3 className="text-lg font-bold mb-3">Pay cost to play Ballaber:</h3>
              <button
                style={
                  useAlternativeCost && !alternativeCostCard
                    ? { boxShadow: '0 0 0 4px rgb(250 204 21), 0 10px 15px -3px rgba(250, 204, 21, 0.5)' }
                    : undefined
                }
                className={`
                  w-full px-4 py-3.5 rounded transition-all text-sm mb-4
                  ${useAlternativeCost && !alternativeCostCard
                    ? 'bg-red-700'
                    : 'bg-red-600 hover:bg-red-700 cursor-pointer'
                  }
                `}
                onClick={selectPayCC}
              >
                <div className="flex justify-between items-center gap-3">
                  <span className="font-medium leading-tight text-left flex-1">
                    Pay {action.cost_cc} CC
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold whitespace-nowrap flex-shrink-0 bg-black bg-opacity-30">
                    {action.cost_cc} CC
                  </span>
                </div>
              </button>
              <h4 className="text-md font-semibold mb-3">Or select a card to sleep:</h4>
              <div className="grid grid-cols-2 gap-3">
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
            </div>
          )}

          {/* Target Selection (for other cards) */}
          {!useAlternativeCost && availableTargets.length > 0 && (
            <div className="p-4">
            <h3 className="text-lg font-bold mb-3">
              {maxTargets > 1
                ? `Select up to ${maxTargets} target${maxTargets !== 1 ? 's' : ''}`
                : 'Select a target '
              }
              {minTargets === 0 && ' (optional)'}
              {selectedTargets.length > 0 && (
                <span className="ml-2 text-yellow-400">
                  ({selectedTargets.length}/{maxTargets} selected)
                </span>
              )}
            </h3>
            <div className="grid grid-cols-2 gap-3">
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
            <div className="p-4 text-center text-gray-400">
              No targets available, but you can still play this card.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

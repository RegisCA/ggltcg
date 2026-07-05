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
import { crayonForColor, costNumeralColor, materialFor } from '../theme/crayon';
import type { Card, ValidAction } from '../types/game';

interface TargetSelectionModalProps {
  action: ValidAction;
  availableTargets: Card[];
  onConfirm: (selectedTargets: string[], alternativeCostCard?: string) => void;
  onCancel: () => void;
  alternativeCostOptions?: Card[]; // For Ballaber
  currentCharge?: number; // Current Charge to determine if Pay Charge option is affordable
  /** Local player's ID: targets render in owner material and carry a
   *  player-name tag (§7.4) — material + name separate yours/theirs even when
   *  both decks share a card. */
  humanPlayerId?: string;
  humanPlayerName?: string;
  opponentName?: string;
}

/** Inline stat line for a Toy target ("6 SPD · 4 STR · 1/3 STA"), or null. */
function statLine(card: Card): string | null {
  if (card.card_type !== 'Toy') return null;
  const sta =
    card.current_stamina != null && card.current_stamina !== card.stamina
      ? `${card.current_stamina}/${card.stamina}`
      : `${card.stamina ?? '-'}`;
  return `${card.speed ?? '-'} SPD · ${card.strength ?? '-'} STR · ${sta} STA`;
}

const PANEL_STYLE: React.CSSProperties = {
  background: '#241E17',
  border: '1.5px solid rgba(242,193,78,.4)',
  borderRadius: '14px',
  padding: '14px',
  maxWidth: '460px',
  color: 'var(--ink-text)',
};

export function TargetSelectionModal({
  action,
  availableTargets,
  onConfirm,
  onCancel,
  alternativeCostOptions,
  currentCharge,
  humanPlayerId,
  humanPlayerName,
  opponentName,
}: TargetSelectionModalProps) {
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [useAlternativeCost, setUseAlternativeCost] = useState(false);
  const [alternativeCostCard, setAlternativeCostCard] = useState<string | null>(null);
  const [useDirectAttack, setUseDirectAttack] = useState(false);

  const maxTargets = action.max_targets || 1;
  const minTargets = action.min_targets || 1;
  // Filter alternative cost options: must be in Play or Hand zone, and not Ballaber itself
  const filteredAlternativeCostOptions = (alternativeCostOptions || []).filter(
    (card) => card.id !== action.card_id && (card.zone === 'Hand' || card.zone === 'InPlay')
  );
  // Show alternative cost UI if the card has alternative cost available (like Ballaber)
  // Even if there are no cards to break, we need to show "Pay Charge" option
  const hasAlternativeCost = action.alternative_cost_available === true;
  const hasCardsToBreak = filteredAlternativeCostOptions.length > 0;
  
  // Check if Pay Charge option is affordable (for Ballaber)
  const canAffordCharge = currentCharge !== undefined && action.cost_charge !== undefined 
    ? currentCharge >= action.cost_charge 
    : true;
  
  // Check if this is a tussle action that includes direct_attack as an option
  const hasDirectAttackOption = action.action_type === 'tussle' && 
    action.target_options?.includes('direct_attack');

  // Reset state when action changes
  useEffect(() => {
    setSelectedTargets([]);
    setAlternativeCostCard(null);
    setUseDirectAttack(false);
    // If alternative cost is available but no cards to break AND can afford Charge, auto-select "Pay Charge"
    if (hasAlternativeCost && !hasCardsToBreak && canAffordCharge) {
      setUseAlternativeCost(true);
    } else {
      setUseAlternativeCost(false);
    }
  }, [action.card_id, hasAlternativeCost, hasCardsToBreak, canAffordCharge]);

  const toggleTarget = (cardId: string) => {
    if (selectedTargets.includes(cardId)) {
      setSelectedTargets(selectedTargets.filter((id) => id !== cardId));
    } else if (selectedTargets.length < maxTargets) {
      setSelectedTargets([...selectedTargets, cardId]);
      setUseDirectAttack(false); // Clear direct attack if selecting a card target
    }
  };

  // Select direct attack option (for Paper Plane and similar cards)
  const selectDirectAttack = () => {
    setUseDirectAttack(true);
    setSelectedTargets([]); // Clear card targets when selecting direct attack
  };

  // Select a card target (clears direct attack selection)
  const selectCardTarget = (cardId: string) => {
    setSelectedTargets([cardId]);
    setUseDirectAttack(false);
  };

  // Only allow one card to be selected for alternative cost
  const selectAlternativeCostCard = (cardId: string) => {
    setAlternativeCostCard(cardId);
    setUseAlternativeCost(true);
    setSelectedTargets([]); // Clear normal targets if switching to alt cost
  };

  // Select to pay Charge instead of breaking a card
  const selectPayCharge = () => {
    setUseAlternativeCost(true);
    setAlternativeCostCard(null);
    setSelectedTargets([]);
  };

  const handleConfirm = () => {
    // Direct attack for tussle actions (Paper Plane, etc.)
    if (useDirectAttack) {
      onConfirm(['direct_attack'], undefined);
      return;
    }
    // Ballaber: if using alt cost with card, must have selected a card
    if (useAlternativeCost && alternativeCostCard) {
      onConfirm([], alternativeCostCard);
      return;
    }
    // Ballaber: paying Charge (useAlternativeCost=true but no card selected)
    if (useAlternativeCost && !alternativeCostCard) {
      onConfirm([], undefined);
      return;
    }
    // Normal targeting
    if (selectedTargets.length < minTargets && minTargets > 0) return;
    onConfirm(selectedTargets, undefined);
  };

  const canConfirm = () => {
    // Direct attack selected
    if (useDirectAttack) {
      return true;
    }
    // Ballaber: if using alt cost, either have Charge selected or a card selected
    if (useAlternativeCost) {
      return true; // Can confirm with just Charge payment or with a card
    }
    // Normal targeting
    if (minTargets === 0) return true;
    return selectedTargets.length >= minTargets && selectedTargets.length <= maxTargets;
  };

  const modalTitle = action.action_type === 'tussle'
    ? `Tussle with ${action.card_name}`
    : `Playing ${action.card_name}`;

  // Confirm names the action + target (§7.4). The frontend doesn't carry the
  // effect verb (e.g. "Break"), so plays read "Play X → Target".
  const selectedNames = selectedTargets
    .map((id) => availableTargets.find((c) => c.id === id)?.name)
    .filter((n): n is string => !!n);
  const confirmLabel = useDirectAttack
    ? 'Direct Attack'
    : useAlternativeCost
      ? `Play ${action.card_name ?? 'card'}`
      : action.action_type === 'tussle'
        ? (selectedNames.length ? `Attack ${selectedNames.join(', ')}` : 'Attack')
        : (selectedNames.length ? `Play ${action.card_name} → ${selectedNames.join(', ')}` : `Play ${action.card_name ?? 'card'}`);

  return (
    <Modal
      isOpen={true}
      onClose={onCancel}
      title={modalTitle}
      closeOnBackdropClick={false}
      closeOnEscape={true}
      panelStyle={PANEL_STYLE}
    >
      <div className="flex flex-col" style={{ maxHeight: '70vh' }}>
        {/* Header (§7.4): action name + charge cost */}
        <div className="flex-shrink-0" style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontFamily: 'var(--font-card-name)', fontSize: '20px', lineHeight: 1, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {action.card_name}
            </span>
            {action.cost_charge !== undefined && (
              <span style={{ color: 'var(--gold)', fontWeight: 700, fontSize: '12px', flexShrink: 0 }}>costs {action.cost_charge} ⚡</span>
            )}
          </div>
          <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>
            {hasAlternativeCost
              ? `Play ${action.card_name}.`
              : `${maxTargets > 1 ? `Choose up to ${maxTargets} targets` : 'Choose a target'}${minTargets === 0 ? ' (optional)' : ''}.`}
            {selectedTargets.length > 0 && (
              <span style={{ color: 'var(--gold)' }}> ({selectedTargets.length}/{maxTargets})</span>
            )}
          </div>
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto" style={{ minHeight: 0 }}>
          {/* Direct Attack option for tussle actions (Paper Plane, etc.) */}
          {hasDirectAttackOption && (
            <div style={{ marginBottom: 'var(--spacing-component-md)' }}>
              <button
                style={{
                  padding: 'var(--spacing-component-sm) var(--spacing-component-md)',
                  marginBottom: 'var(--spacing-component-sm)',
                  borderWidth: useDirectAttack ? '3px' : '2px',
                  borderStyle: 'solid',
                  borderColor: useDirectAttack ? '#FFD700' : 'transparent',
                  boxShadow: useDirectAttack 
                    ? '0 0 12px rgba(255, 215, 0, 0.9), 0 0 24px rgba(255, 215, 0, 0.5)' 
                    : 'none',
                }}
                className={`
                  w-full rounded transition-all text-sm focus:ring-2 focus:ring-yellow-400
                  ${useDirectAttack
                    ? 'bg-red-700'
                    : 'bg-red-600 hover:bg-red-700 cursor-pointer'
                  }
                `}
                onClick={selectDirectAttack}
              >
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <span className="font-medium leading-tight text-left flex-1">
                    🎯 Direct Attack
                  </span>
                  <span 
                    className="rounded text-xs font-bold whitespace-nowrap flex-shrink-0 bg-black bg-opacity-30"
                    style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-xs)' }}
                  >
                    Random from hand
                  </span>
                </div>
              </button>
              {availableTargets.length > 0 && (
                <p className="text-sm text-gray-400" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
                  Or select a card to tussle:
                </p>
              )}
            </div>
          )}

          {/* Ballaber alternative cost: one-click selection */}
          {hasAlternativeCost && (
            <div style={{ marginBottom: 'var(--spacing-component-md)' }}>
              <h3 className="text-lg font-bold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Pay cost to play Ballaber:</h3>
              <button
                disabled={!canAffordCharge}
                style={{
                  ...(useAlternativeCost && !alternativeCostCard && canAffordCharge
                    ? { boxShadow: '0 0 0 4px rgb(250 204 21), 0 10px 15px -3px rgba(250, 204, 21, 0.5)' }
                    : {}),
                  padding: 'var(--spacing-component-sm) var(--spacing-component-md)',
                  marginBottom: 'var(--spacing-component-md)'
                }}
                className={`
                  w-full rounded transition-all text-sm focus:ring-2 focus:ring-yellow-400
                  ${!canAffordCharge
                    ? 'bg-gray-600 opacity-50 cursor-not-allowed'
                    : useAlternativeCost && !alternativeCostCard
                      ? 'bg-red-700'
                      : 'bg-red-600 hover:bg-red-700 cursor-pointer'
                  }
                `}
                onClick={canAffordCharge ? selectPayCharge : undefined}
              >
                <div className="flex justify-between items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
                  <span className="font-medium leading-tight text-left flex-1">
                    {canAffordCharge ? `Pay ${action.cost_charge} Charge` : `🔒 Pay ${action.cost_charge} Charge (not enough Charge)`}
                  </span>
                  <span 
                    className="rounded text-xs font-bold whitespace-nowrap flex-shrink-0 bg-black bg-opacity-30"
                    style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-xs)' }}
                  >
                    {action.cost_charge} Charge
                  </span>
                </div>
              </button>
              {hasCardsToBreak ? (
                <>
                  <h4 className="text-md font-semibold" style={{ marginBottom: 'var(--spacing-component-sm)' }}>Or select a card to break:</h4>
                  <div 
                    className="grid grid-cols-2" 
                    style={{ 
                      gap: 'var(--spacing-component-md)', 
                      padding: 'var(--spacing-component-sm)',
                      paddingBottom: 'var(--spacing-component-lg)'
                    }}
                  >
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
                  No cards available to break. You must pay {action.cost_charge} Charge.
                </p>
              )}
            </div>
          )}

          {/* Target Selection (for other cards) */}
          {!useAlternativeCost && availableTargets.length > 0 && (
            <div>
              {/* Prompt + count live in the header now; direct-attack keeps its
                  own "or select a card" line above this grid. */}
              <div
                className="grid grid-cols-2"
                style={{ gap: '9px' }}
              >
                {availableTargets.map((card) => {
                  const isSelected = selectedTargets.includes(card.id);
                  const isDisabled = !isSelected && selectedTargets.length >= maxTargets;
                  const clickable = !isDisabled || hasDirectAttackOption;
                  // For tussle with direct attack option, use single-select behavior
                  const handleClick = hasDirectAttackOption
                    ? () => selectCardTarget(card.id)
                    : () => !isDisabled && toggleTarget(card.id);
                  // Material + name tag from OWNER (§1/§7.4), not controller.
                  const own = card.owner === humanPlayerId;
                  const crayon = crayonForColor(card.primary_color);
                  const material = materialFor(own);
                  const stats = statLine(card);
                  const tagName = own ? (humanPlayerName || 'You') : (opponentName || 'Opponent');
                  return (
                    <div
                      key={card.id}
                      onClick={clickable ? handleClick : undefined}
                      style={{
                        position: 'relative',
                        background: material.surface,
                        color: material.text,
                        border: `2px solid ${crayon}`,
                        borderRadius: '6px',
                        padding: '7px 8px',
                        outline: isSelected ? '3px solid var(--gold)' : undefined,
                        outlineOffset: isSelected ? '2px' : undefined,
                        cursor: clickable ? 'pointer' : 'not-allowed',
                        opacity: clickable ? 1 : 0.5,
                      }}
                    >
                      {isSelected && (
                        <div style={{ position: 'absolute', top: '-9px', right: '-9px', width: '20px', height: '20px', background: 'var(--gold)', color: 'var(--desk-bottom)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '11px' }}>✓</div>
                      )}
                      {humanPlayerId && (
                        <div style={{ display: 'inline-block', background: own ? 'var(--you)' : 'var(--them)', color: own ? '#1A2536' : '#241A33', fontSize: '8px', fontWeight: 900, letterSpacing: '.06em', borderRadius: '3px', padding: '1px 5px', marginBottom: '5px' }}>
                          {tagName}
                        </div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '18px', height: '18px', background: crayon, color: costNumeralColor(crayon, own), borderRadius: '3px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '11px', flexShrink: 0 }}>
                          {card.effective_cost ?? card.cost}
                        </div>
                        <span style={{ fontFamily: 'var(--font-card-name)', fontSize: '15px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{card.name}</span>
                      </div>
                      {stats && (
                        <div style={{ fontSize: '9.5px', color: material.textFaint, marginTop: '4px', fontWeight: 700 }}>{stats}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!useAlternativeCost && availableTargets.length === 0 && minTargets === 0 && !hasAlternativeCost && (
            <div style={{ textAlign: 'center', color: 'var(--ink-muted)', fontSize: '11.5px' }}>
              No targets available, but you can still play this card.
            </div>
          )}
        </div>

        {/* Cancel / named-confirm (§7.4) */}
        <div className="flex-shrink-0" style={{ display: 'flex', gap: '9px', marginTop: '14px' }}>
          <button
            onClick={onCancel}
            style={{ flex: 1, textAlign: 'center', border: '1.5px solid rgba(237,232,222,.3)', color: 'rgba(237,232,222,.7)', fontWeight: 700, fontSize: '12px', padding: '10px 0', borderRadius: '6px', background: 'none', cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm()}
            style={{ flex: 2, textAlign: 'center', background: 'var(--gold)', color: '#211a13', fontWeight: 900, fontSize: '13px', padding: '10px 0', borderRadius: '6px', boxShadow: '0 3px 0 rgba(0,0,0,.5)', border: 'none', cursor: canConfirm() ? 'pointer' : 'not-allowed', opacity: canConfirm() ? 1 : 0.5 }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}

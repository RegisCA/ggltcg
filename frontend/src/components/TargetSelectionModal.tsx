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
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import type { Card, ValidAction } from '../types/game';

interface TargetSelectionModalProps {
  action: ValidAction;
  availableTargets: Card[];
  onConfirm: (selectedTargets: string[], alternativeCostCard?: string) => void;
  onCancel: () => void;
  alternativeCostOptions?: Card[]; // For Ballaber
  currentCharge?: number; // Current Charge to determine if Pay Charge option is affordable
  /** Opponent's display name, for the "…'s In play" group header. */
  opponentName?: string;
}

// Group targets by WHOSE zone they're in. The card material already shows the
// owner, but "In play" alone is ambiguous — both players have an in-play zone —
// so each group names the side + zone (matching the board zone headers).
// In-play membership follows the controller (whose board it sits on); break and
// hand follow the owner. Full cards so the effect text stays readable.
function targetGroup(card: Card, localId: string | null, opp: string): { order: number; label: string } {
  if (card.zone === 'InPlay') {
    const mine = card.controller === localId;
    return { order: mine ? 0 : 1, label: `${mine ? 'You' : opp} · In play` };
  }
  if (card.zone === 'Break') {
    const mine = card.owner === localId;
    return { order: mine ? 2 : 3, label: `${mine ? 'You' : opp} · Break zone` };
  }
  const mine = card.owner === localId;
  return { order: mine ? 4 : 5, label: mine ? 'Your hand' : `${opp} · Hand` };
}

const PANEL_STYLE: React.CSSProperties = {
  background: '#241E17',
  border: '1.5px solid rgba(242,193,78,.4)',
  borderRadius: '14px',
  padding: '14px',
  maxWidth: '460px',
  color: 'var(--ink-text)',
};

// When a target set mixes Toys and Actions across zone groups, give every card
// this shared min-height so Actions (no stat rail) match the Toy height — the
// per-group grids can't equalize across groups on their own. A medium Toy is
// rail-dominated (the 3 stat boxes sit beside the effect, so it's ~131px tall
// regardless of effect length); this sits just above that.
const MIXED_CARD_MIN_HEIGHT = 134;

export function TargetSelectionModal({
  action,
  availableTargets,
  onConfirm,
  onCancel,
  alternativeCostOptions,
  currentCharge,
  opponentName,
}: TargetSelectionModalProps) {
  const localId = useLocalPlayerId();
  // Equal card heights only matter when a Toy is present (Toys are the tall
  // ones); an all-Action target set stays content-height.
  const targetCardMinHeight = availableTargets.some((c) => c.card_type === 'Toy') ? MIXED_CARD_MIN_HEIGHT : undefined;
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

          {/* Ballaber alternative cost */}
          {hasAlternativeCost && (
            <div>
              {/* Pay-Charge option. Selection is a border (in-box), not an
                  outward ring — an outward ring gets clipped by the scroll edge. */}
              <button
                disabled={!canAffordCharge}
                onClick={canAffordCharge ? selectPayCharge : undefined}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                  padding: '9px 12px',
                  marginBottom: '12px',
                  borderRadius: '8px',
                  border: `2px solid ${useAlternativeCost && !alternativeCostCard && canAffordCharge ? 'var(--gold)' : 'rgba(237,232,222,.18)'}`,
                  background: useAlternativeCost && !alternativeCostCard && canAffordCharge ? 'rgba(242,193,78,.12)' : 'rgba(237,232,222,.04)',
                  color: canAffordCharge ? 'var(--ink-text)' : 'var(--ink-faint)',
                  cursor: canAffordCharge ? 'pointer' : 'not-allowed',
                  opacity: canAffordCharge ? 1 : 0.6,
                }}
              >
                <span style={{ fontWeight: 700, fontSize: '13px', textAlign: 'left' }}>
                  {canAffordCharge ? `Pay ${action.cost_charge} Charge` : `Pay ${action.cost_charge} Charge — not enough`}
                </span>
                <span style={{ flexShrink: 0, color: 'var(--gold)', fontWeight: 900, fontSize: '13px' }}>⚡{action.cost_charge}</span>
              </button>

              {hasCardsToBreak ? (
                <>
                  <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)', marginBottom: '2px' }}>
                    Or break one of your cards to play it free:
                  </div>
                  {/* Grouped by zone — the break options mix in-play and hand
                      cards, and it matters which one you're about to break. */}
                  {(() => {
                    const opp = opponentName || 'Opponent';
                    const groups = new Map<number, { label: string; cards: Card[] }>();
                    for (const card of filteredAlternativeCostOptions) {
                      const g = targetGroup(card, localId, opp);
                      if (!groups.has(g.order)) groups.set(g.order, { label: g.label, cards: [] });
                      groups.get(g.order)!.cards.push(card);
                    }
                    const ordered = [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([, v]) => v);
                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {ordered.map((grp) => (
                          <div key={grp.label}>
                            <div style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: '2px' }}>
                              {grp.label}
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', padding: '10px 10px 4px' }}>
                              {grp.cards.map((card) => {
                                const isSelected = alternativeCostCard === card.id;
                                return (
                                  <div key={card.id} style={{ position: 'relative', zIndex: isSelected ? 2 : 1, display: 'flex', justifyContent: 'center' }}>
                                    <CardDisplay
                                      card={card}
                                      size="medium"
                                      fluid
                                      minHeight={filteredAlternativeCostOptions.some((c) => c.card_type === 'Toy') ? MIXED_CARD_MIN_HEIGHT : undefined}
                                      isSelected={isSelected}
                                      isClickable
                                      onClick={() => selectAlternativeCostCard(card.id)}
                                      disableDetailModal
                                    />
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </>
              ) : (
                <div style={{ color: 'var(--ink-muted)', fontSize: '11.5px' }}>
                  No cards available to break. You must pay {action.cost_charge} Charge.
                </div>
              )}
            </div>
          )}

          {/* Target selection — grouped by WHICH side's zone (You · In play /
              {opp} · In play / … · Break zone / Your hand). Owner is also shown
              by the card material; the group gives the zone context. */}
          {!useAlternativeCost && availableTargets.length > 0 && (() => {
            const opp = opponentName || 'Opponent';
            const groups = new Map<number, { label: string; cards: Card[] }>();
            for (const card of availableTargets) {
              const g = targetGroup(card, localId, opp);
              if (!groups.has(g.order)) groups.set(g.order, { label: g.label, cards: [] });
              groups.get(g.order)!.cards.push(card);
            }
            const ordered = [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([, v]) => v);
            return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {ordered.map((grp) => (
                <div key={grp.label}>
                  <div style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: '2px' }}>
                    {grp.label}
                  </div>
                  {/* padding leaves room for the selected ✓ badge (which sits
                      proud of the card corner) so it isn't clipped by the scroll
                      edge or covered by the neighbouring card. */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', padding: '10px 10px 4px' }}>
                    {grp.cards.map((card) => {
                      const isSelected = selectedTargets.includes(card.id);
                      const isDisabled = !isSelected && selectedTargets.length >= maxTargets;
                      const clickable = !isDisabled || hasDirectAttackOption;
                      const handleClick = hasDirectAttackOption
                        ? () => selectCardTarget(card.id)
                        : () => !isDisabled && toggleTarget(card.id);
                      return (
                        <div key={card.id} style={{ position: 'relative', zIndex: isSelected ? 2 : 1, display: 'flex', justifyContent: 'center' }}>
                          <CardDisplay
                            card={card}
                            size="medium"
                            fluid
                            minHeight={targetCardMinHeight}
                            isSelected={isSelected}
                            isClickable={clickable}
                            isDisabled={isDisabled && !hasDirectAttackOption}
                            onClick={clickable ? handleClick : undefined}
                            disableDetailModal
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
            );
          })()}

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

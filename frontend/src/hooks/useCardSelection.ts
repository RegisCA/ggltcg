/**
 * useCardSelection — one selection primitive for target/alt-cost pickers.
 *
 * Unifies what used to be three near-duplicate handlers in
 * TargetSelectionModal (toggleTarget / selectCardTarget / selectAlternativeCostCard):
 *
 * - maxTargets === 1: clicking a card REPLACES the selection; clicking the
 *   already-selected card deselects it (no more "stuck" single-select where
 *   you had to deselect before picking a different card).
 * - maxTargets > 1: toggle semantics; adding beyond max is a no-op.
 *
 * `clear()` resets the selection — used on Cancel/close so a past bug
 * ("Cancel leaves the card selected") can't come back.
 */
import { useCallback, useState } from 'react';

export interface UseCardSelection {
  selected: string[];
  select: (cardId: string) => void;
  clear: () => void;
  isSelected: (cardId: string) => boolean;
  /** True when a (different, unselected) card can't be added — multi-select
   *  at capacity. Single-select never disables other cards. */
  isDisabled: (cardId: string) => boolean;
}

export function useCardSelection(maxTargets: number): UseCardSelection {
  const [selected, setSelected] = useState<string[]>([]);

  const select = useCallback((cardId: string) => {
    setSelected((prev) => {
      const already = prev.includes(cardId);
      if (maxTargets <= 1) {
        // Replace semantics: clicking the selected card deselects it,
        // clicking any other card replaces the selection.
        return already ? [] : [cardId];
      }
      // Multi-select toggle: ignore adds past the cap.
      if (already) return prev.filter((id) => id !== cardId);
      if (prev.length >= maxTargets) return prev;
      return [...prev, cardId];
    });
  }, [maxTargets]);

  const clear = useCallback(() => setSelected([]), []);

  const isSelected = useCallback((cardId: string) => selected.includes(cardId), [selected]);

  const isDisabled = useCallback(
    (cardId: string) => maxTargets > 1 && !selected.includes(cardId) && selected.length >= maxTargets,
    [maxTargets, selected]
  );

  return { selected, select, clear, isSelected, isDisabled };
}

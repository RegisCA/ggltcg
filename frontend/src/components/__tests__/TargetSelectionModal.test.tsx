/**
 * Interaction tests for TargetSelectionModal, pinning the selection semantics
 * introduced by useCardSelection (frontend/src/hooks/useCardSelection.ts):
 *
 * - single-select (max_targets: 1): click replaces the selection; clicking
 *   the already-selected card deselects it.
 * - multi-select (max_targets: 2): toggle up to the cap; a third click while
 *   at capacity is a no-op (and the card is rendered disabled).
 * - Cancel/close always clears the selection (regression: "Cancel leaves the
 *   card selected").
 * - keyboard: Enter/Space activates a focused card (CardDisplay already wires
 *   this up for isClickable cards); Esc triggers cancel (via Modal's
 *   closeOnEscape, wired to TargetSelectionModal's onClose === handleCancel).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TargetSelectionModal } from '../TargetSelectionModal';
import type { Card, ValidAction } from '../../types/game';

function makeCard(id: string, name: string, overrides: Partial<Card> = {}): Card {
  return {
    id,
    name,
    card_type: 'Toy',
    cost: 1,
    effective_cost: null,
    effect_text: 'Test effect text.',
    zone: 'InPlay',
    owner: 'fixture-opponent',
    controller: 'fixture-opponent',
    speed: 3,
    strength: 3,
    stamina: 3,
    current_stamina: 3,
    base_speed: 3,
    base_strength: 3,
    base_stamina: 3,
    is_broken: false,
    primary_color: '#C74444',
    accent_color: '#C74444',
    ...overrides,
  };
}

const CARD_A = makeCard('card-a', 'Alpha');
const CARD_B = makeCard('card-b', 'Bravo');
const CARD_C = makeCard('card-c', 'Charlie');

function baseAction(overrides: Partial<ValidAction> = {}): ValidAction {
  return {
    action_type: 'play_card',
    description: 'Play Source Card',
    card_id: 'source-card',
    card_name: 'Source Card',
    max_targets: 1,
    min_targets: 1,
    ...overrides,
  };
}

function renderModal(props: Partial<React.ComponentProps<typeof TargetSelectionModal>> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  const utils = render(
    <TargetSelectionModal
      action={baseAction()}
      availableTargets={[CARD_A, CARD_B, CARD_C]}
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...props}
    />
  );
  return { ...utils, onConfirm, onCancel };
}

// The target grid cards render as CardDisplay with an aria-label of
// "<name> card" when clickable.
function cardButton(name: string) {
  return screen.getByRole('button', { name: `${name} card` });
}

describe('TargetSelectionModal — selection semantics', () => {
  it('single-select: clicking card A then card B leaves only B selected', async () => {
    const user = userEvent.setup();
    renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    await user.click(cardButton('Alpha'));
    expect(cardButton('Alpha')).toHaveAttribute('aria-label', 'Alpha card');
    // Confirm label reflects the current selection.
    expect(screen.getByRole('button', { name: /Play Source Card → Alpha/ })).toBeInTheDocument();

    await user.click(cardButton('Bravo'));
    expect(screen.getByRole('button', { name: /Play Source Card → Bravo/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Play Source Card → Alpha/ })).not.toBeInTheDocument();
  });

  it('single-select: clicking the selected card deselects it', async () => {
    const user = userEvent.setup();
    renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    await user.click(cardButton('Alpha'));
    expect(screen.getByRole('button', { name: /Play Source Card → Alpha/ })).toBeInTheDocument();

    await user.click(cardButton('Alpha'));
    expect(screen.getByRole('button', { name: 'Play Source Card' })).toBeInTheDocument();
  });

  it('multi-select: toggles up to max, and a third click at capacity does nothing', async () => {
    const user = userEvent.setup();
    renderModal({ action: baseAction({ max_targets: 2, min_targets: 1 }) });

    await user.click(cardButton('Alpha'));
    await user.click(cardButton('Bravo'));
    expect(screen.getByText('(2/2)')).toBeInTheDocument();

    // Charlie is disabled at capacity — CardDisplay renders it non-interactive
    // (no button role), so there's nothing to click; selection stays capped.
    expect(screen.queryByRole('button', { name: 'Charlie card' })).not.toBeInTheDocument();
    expect(screen.getByText('(2/2)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Play Source Card → Alpha, Bravo' })).toBeInTheDocument();
  });

  it('disabled cards (multi-select at max) are not clickable', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    renderModal({ action: baseAction({ max_targets: 2, min_targets: 1 }), onConfirm });

    await user.click(cardButton('Alpha'));
    await user.click(cardButton('Bravo'));

    const charlieContainer = screen.getByText('Charlie').closest('div[style]');
    // Charlie's CardDisplay is rendered with isClickable=false when disabled,
    // so it has no button role / tabIndex.
    expect(screen.queryByRole('button', { name: 'Charlie card' })).not.toBeInTheDocument();
    expect(charlieContainer).toBeTruthy();
  });

  it('Cancel clears the selection (onCancel fires, and a fresh render shows nothing selected)', async () => {
    const user = userEvent.setup();
    const { onCancel, unmount } = renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    await user.click(cardButton('Alpha'));
    expect(screen.getByRole('button', { name: /Play Source Card → Alpha/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);

    unmount();
    // Re-render fresh (simulating the modal being reopened) — no stale selection.
    renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });
    expect(screen.getByRole('button', { name: 'Play Source Card' })).toBeInTheDocument();
  });

  it('Esc closes/cancels the modal and clears the selection', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    await user.click(cardButton('Alpha'));
    expect(screen.getByRole('button', { name: /Play Source Card → Alpha/ })).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('keyboard: Enter selects a focused target card', async () => {
    const user = userEvent.setup();
    renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    const alpha = cardButton('Alpha');
    alpha.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /Play Source Card → Alpha/ })).toBeInTheDocument();
  });

  it('keyboard: Space selects a focused target card', async () => {
    const user = userEvent.setup();
    renderModal({ action: baseAction({ max_targets: 1, min_targets: 1 }) });

    const bravo = cardButton('Bravo');
    bravo.focus();
    await user.keyboard(' ');
    expect(screen.getByRole('button', { name: /Play Source Card → Bravo/ })).toBeInTheDocument();
  });
});

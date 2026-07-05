/**
 * Smoke test for CardDetailModal: renders the card's name and effect text,
 * and fires onAction (then closes) when the action button is clicked.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CardDetailModal } from '../CardDetailModal';
import type { Card } from '../../types/game';

const CARD: Card = {
  id: 'test-card-1',
  name: 'Archer',
  card_type: 'Toy',
  cost: 0,
  effective_cost: null,
  effect_text: "This card can't start tussles. You may spend Charge to remove stamina from cards.",
  zone: 'Hand',
  owner: 'player1',
  controller: 'player1',
  speed: 0,
  strength: 0,
  stamina: 5,
  current_stamina: 5,
  base_speed: 0,
  base_strength: 0,
  base_stamina: 5,
  is_broken: false,
  primary_color: '#C74444',
  accent_color: '#C74444',
};

describe('CardDetailModal', () => {
  it('renders the card name and effect text', () => {
    render(<CardDetailModal card={CARD} isOpen={true} onClose={vi.fn()} />);

    expect(screen.getAllByText('Archer').length).toBeGreaterThan(0);
    expect(screen.getByText(CARD.effect_text)).toBeInTheDocument();
  });

  it('fires onAction and closes when the action button is clicked', async () => {
    const onAction = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <CardDetailModal
        card={CARD}
        isOpen={true}
        onClose={onClose}
        onAction={onAction}
        actionLabel="Select"
      />
    );

    await user.click(screen.getByRole('button', { name: 'Select' }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not render when closed', () => {
    render(<CardDetailModal card={CARD} isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByText(CARD.effect_text)).not.toBeInTheDocument();
  });
});

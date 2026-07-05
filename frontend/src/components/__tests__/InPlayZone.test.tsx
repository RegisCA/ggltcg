/**
 * InPlayZone: renders in-play cards, and flags a card that newly arrives
 * (present now but absent on the previous render) with a transient gold
 * arrival ring. Cards present since the first render never get the ring —
 * that would flash the whole board on mid-game mount.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InPlayZone } from '../InPlayZone';
import type { Card } from '../../types/game';

function makeCard(id: string, name: string): Card {
  return {
    id,
    name,
    card_type: 'creature',
    cost: 1,
    effective_cost: null,
    effect_text: '',
    zone: 'in_play',
    owner: 'player1',
    controller: 'player1',
    speed: null,
    strength: null,
    stamina: null,
    current_stamina: null,
    base_speed: null,
    base_strength: null,
  } as unknown as Card;
}

describe('InPlayZone', () => {
  it('renders cards passed in', () => {
    const cards = [makeCard('c1', 'Knight'), makeCard('c2', 'Archer')];
    render(<InPlayZone cards={cards} playerName="Régis" />);
    expect(screen.getByText('Knight')).toBeInTheDocument();
    expect(screen.getByText('Archer')).toBeInTheDocument();
  });

  it('shows the empty state when there are no cards', () => {
    render(<InPlayZone cards={[]} playerName="Régis" />);
    expect(screen.getByText('No cards in play')).toBeInTheDocument();
  });

  it('does not flash arrival on the initial render, even mid-game', () => {
    const cards = [makeCard('c1', 'Knight'), makeCard('c2', 'Archer')];
    render(<InPlayZone cards={cards} playerName="Régis" />);
    expect(screen.queryAllByTestId('arrival-flash')).toHaveLength(0);
  });

  it('flags a card added on rerender with the arrival overlay, but not the pre-existing card', () => {
    const cards = [makeCard('c1', 'Knight')];
    const { rerender } = render(<InPlayZone cards={cards} playerName="Régis" />);
    expect(screen.queryAllByTestId('arrival-flash')).toHaveLength(0);

    const updated = [makeCard('c1', 'Knight'), makeCard('c2', 'Archer')];
    rerender(<InPlayZone cards={updated} playerName="Régis" />);

    const flashes = screen.getAllByTestId('arrival-flash');
    expect(flashes).toHaveLength(1);
  });

  it('removes the arrival overlay after the animation window elapses', async () => {
    const cards = [makeCard('c1', 'Knight')];
    const { rerender } = render(<InPlayZone cards={cards} playerName="Régis" />);

    const updated = [makeCard('c1', 'Knight'), makeCard('c2', 'Archer')];
    rerender(<InPlayZone cards={updated} playerName="Régis" />);
    expect(screen.getAllByTestId('arrival-flash')).toHaveLength(1);

    // Real timers: the component clears the overlay via setTimeout after
    // ARRIVAL_DURATION_MS (800ms). Wait past that window.
    await new Promise((resolve) => setTimeout(resolve, 900));
    expect(screen.queryAllByTestId('arrival-flash')).toHaveLength(0);
  }, 2000);
});

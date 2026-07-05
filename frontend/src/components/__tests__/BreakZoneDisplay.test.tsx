/**
 * BreakZoneDisplay: empty state, count badge, newest-first chips, the
 * 4-chip + "+n" overflow rule, and the modal open affordance.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BreakZoneDisplay } from '../BreakZoneDisplay';
import type { Card } from '../../types/game';

function makeCard(id: string, name: string): Card {
  return {
    id,
    name,
    card_type: 'creature',
    cost: 1,
    effective_cost: null,
    effect_text: '',
    zone: 'break',
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

describe('BreakZoneDisplay', () => {
  it('shows the empty state when there are no broken cards', () => {
    render(<BreakZoneDisplay cards={[]} playerName="Régis" />);
    expect(screen.getByText('empty')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows a count badge and chip for a single broken card', () => {
    const cards = [makeCard('c1', 'Knight')];
    render(<BreakZoneDisplay cards={cards} playerName="Régis" />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('Knight')).toBeInTheDocument();
  });

  it('renders chips newest-first', () => {
    const cards = [makeCard('c1', 'Knight'), makeCard('c2', 'Archer'), makeCard('c3', 'Mage')];
    render(<BreakZoneDisplay cards={cards} playerName="Régis" />);
    const chips = screen.getAllByText(/Knight|Archer|Mage/);
    expect(chips.map((el) => el.textContent)).toEqual(['Mage', 'Archer', 'Knight']);
  });

  it('caps at 4 chips and shows a "+n" overflow chip for larger piles', () => {
    const cards = [
      makeCard('c1', 'Knight'),
      makeCard('c2', 'Archer'),
      makeCard('c3', 'Mage'),
      makeCard('c4', 'Rogue'),
      makeCard('c5', 'Cleric'),
      makeCard('c6', 'Bard'),
    ];
    render(<BreakZoneDisplay cards={cards} playerName="Régis" />);
    // Newest first: Bard, Cleric, Rogue, Mage visible; Archer, Knight hidden behind +2.
    expect(screen.getByText('Bard')).toBeInTheDocument();
    expect(screen.getByText('Cleric')).toBeInTheDocument();
    expect(screen.getByText('Rogue')).toBeInTheDocument();
    expect(screen.getByText('Mage')).toBeInTheDocument();
    expect(screen.queryByText('Archer')).not.toBeInTheDocument();
    expect(screen.queryByText('Knight')).not.toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('opens the modal when the slat is clicked', async () => {
    const { user } = await import('@testing-library/user-event').then((m) => ({ user: m.default.setup() }));
    const cards = [makeCard('c1', 'Knight')];
    render(<BreakZoneDisplay cards={cards} playerName="Régis" />);

    expect(screen.queryByText('Régis · Break Zone (1)')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Régis · Break Zone (1)')).toBeInTheDocument();
  });
});

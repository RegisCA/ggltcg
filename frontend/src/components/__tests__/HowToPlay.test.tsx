/**
 * Smoke test for HowToPlay: renders key section headings on the default tab
 * and switches tabs to reveal other sections' headings.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HowToPlay } from '../HowToPlay';

describe('HowToPlay', () => {
  it('renders the Overview tab headings by default', () => {
    render(<HowToPlay isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Objective')).toBeInTheDocument();
    expect(screen.getByText('Charge')).toBeInTheDocument();
    expect(screen.getByText('Turn Structure')).toBeInTheDocument();
  });

  it('switches to the Tussling tab and shows its headings', async () => {
    const user = userEvent.setup();
    render(<HowToPlay isOpen={true} onClose={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Tussling' }));

    expect(screen.getByText('How Tussles Work')).toBeInTheDocument();
    expect(screen.getByText('Choosing Targets')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<HowToPlay isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByText('Objective')).not.toBeInTheDocument();
  });
});

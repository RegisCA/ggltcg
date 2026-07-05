/**
 * Smoke test for LobbyWaiting: waiting-room state shows both players via the
 * initialPhaseOverride/currentPlayerReadyOverride seam (same seam the
 * /design.html#lobby-waiting fixture uses to avoid live polling).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LobbyWaiting } from '../LobbyWaiting';

describe('LobbyWaiting', () => {
  it('shows both players and the current player as ready in the waiting-for-decks phase', () => {
    render(
      <LobbyWaiting
        gameId="test-game"
        gameCode="9P47XA"
        actualPlayerId="player-1-id"
        currentPlayerId="player1"
        currentPlayerName="You"
        otherPlayerName="Gemiknight"
        onGameStarted={vi.fn()}
        onBack={vi.fn()}
        initialPhaseOverride="waiting-for-decks"
        currentPlayerReadyOverride={true}
      />
    );

    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByText('Gemiknight')).toBeInTheDocument();
    expect(screen.getByText('Deck Ready')).toBeInTheDocument();
    expect(screen.getByText(/waiting for player 2 to select their deck/i)).toBeInTheDocument();
  });

  it('renders the shareable game code', () => {
    render(
      <LobbyWaiting
        gameId="test-game"
        gameCode="9P47XA"
        actualPlayerId="player-1-id"
        currentPlayerId="player1"
        currentPlayerName="You"
        otherPlayerName={null}
        onGameStarted={vi.fn()}
        onBack={vi.fn()}
        initialPhaseOverride="waiting-for-player"
      />
    );

    expect(screen.getByText('9P47XA')).toBeInTheDocument();
  });
});

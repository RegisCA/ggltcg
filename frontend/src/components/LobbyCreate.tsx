/**
 * Lobby Create Component
 *
 * Create a new game lobby and display game code for sharing. Restyled to the
 * Paper & Ink language: desk gradient, Gochi Hand title, dark panel form,
 * gold primary button (§7.2 idiom), gold-hairline info panel.
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { createLobby } from '../api/gameService';

interface LobbyCreateProps {
  onLobbyCreated: (gameId: string, gameCode: string) => void;
  onBack: () => void;
}

export function LobbyCreate({ onLobbyCreated, onBack }: LobbyCreateProps) {
  const { user } = useAuth();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playerName = user?.display_name || 'Player';
  const playerId = user?.google_id || '';

  const handleCreate = async () => {
    if (!playerId) {
      setError('You must be logged in to create a game');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const response = await createLobby({
        player1_id: playerId,
        player1_name: playerName,
      });
      onLobbyCreated(response.game_id, response.game_code);
    } catch (err: unknown) {
      console.error('Failed to create lobby:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any).response?.data?.detail || 'Failed to create lobby. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        padding: 'var(--spacing-component-md)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      <div className="max-w-md w-full">
        {/* Back Button */}
        <div style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <button
            onClick={onBack}
            className="flex items-center transition-colors"
            style={{
              gap: 'var(--spacing-component-xs)',
              color: 'var(--ink-muted)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '13px',
            }}
          >
            <span>←</span> Back to Main Menu
          </button>
        </div>

        {/* Title */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-card-name)',
              fontSize: 'clamp(36px, 7vw, 48px)',
              lineHeight: 1,
              marginBottom: 'var(--spacing-component-sm)',
              color: 'var(--ink-text)',
            }}
          >
            Create Game
          </h1>
          <p style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink-muted)' }}>
            Start a new game as <span style={{ color: 'var(--you)' }}>{playerName}</span>
          </p>
        </div>

        {/* Form */}
        <div
          style={{
            background: 'var(--color-panel)',
            borderRadius: '8px',
            border: '1px solid rgba(242,193,78,.25)',
            padding: 'var(--spacing-component-xl)',
          }}
        >
          <div className="content-spacing">
            {/* Error Message */}
            {error && (
              <div
                style={{
                  background: 'rgba(224,113,107,.12)',
                  border: '1px solid var(--danger)',
                  borderRadius: '6px',
                  color: 'var(--danger)',
                  padding: 'var(--spacing-component-sm)',
                  fontSize: '13px',
                  fontWeight: 700,
                }}
              >
                {error}
              </div>
            )}

            {/* Create Button */}
            <button
              onClick={handleCreate}
              disabled={isCreating}
              style={{
                width: '100%',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 900,
                fontSize: '18px',
                padding: 'var(--spacing-component-md) 0',
                background: isCreating ? 'rgba(237,232,222,.15)' : 'var(--gold)',
                color: isCreating ? 'var(--ink-faint)' : 'var(--desk-bottom)',
                boxShadow: isCreating ? 'none' : '0 3px 0 rgba(0,0,0,.5)',
                cursor: isCreating ? 'not-allowed' : 'pointer',
              }}
            >
              {isCreating ? 'Creating Lobby...' : 'Create Lobby'}
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div
          style={{
            background: 'rgba(180,142,222,.08)',
            border: '1px solid rgba(180,142,222,.3)',
            borderRadius: '8px',
            marginTop: 'var(--spacing-component-lg)',
            padding: 'var(--spacing-component-md)',
          }}
        >
          <p style={{ fontWeight: 900, fontSize: '13px', color: 'var(--them)', marginBottom: 'var(--spacing-component-xs)' }}>
            What happens next?
          </p>
          <ul className="content-spacing" style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>
            <li>• You'll receive a 6-character game code</li>
            <li>• Share the code with your friend</li>
            <li>• Both players select decks</li>
            <li>• Game starts automatically!</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

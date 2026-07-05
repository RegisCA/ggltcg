/**
 * Lobby Join Component
 *
 * Join an existing game lobby using a game code. Restyled to the Paper & Ink
 * language: desk gradient, Gochi Hand title, dark panel form with a mono
 * code-entry field, gold primary button (§7.2 idiom).
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { joinLobby } from '../api/gameService';

interface LobbyJoinProps {
  onLobbyJoined: (gameId: string, gameCode: string, player1Name: string, player1Id: string) => void;
  onBack: () => void;
}

export function LobbyJoin({ onLobbyJoined, onBack }: LobbyJoinProps) {
  const { user } = useAuth();
  const [gameCode, setGameCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playerName = user?.display_name || 'Player';
  const playerId = user?.google_id || '';

  const handleJoin = async () => {
    if (!playerId) {
      setError('You must be logged in to join a game');
      return;
    }

    if (!gameCode.trim()) {
      setError('Please enter a game code');
      return;
    }

    // Validate game code format (6 alphanumeric characters)
    const cleanCode = gameCode.trim().toUpperCase();
    if (!/^[A-Z0-9]{6}$/.test(cleanCode)) {
      setError('Game code must be 6 characters (letters and numbers only)');
      return;
    }

    setIsJoining(true);
    setError(null);

    try {
      const response = await joinLobby(cleanCode, {
        player2_id: playerId,
        player2_name: playerName,
      });
      onLobbyJoined(response.game_id, response.game_code, response.player1_name, response.player1_id);
    } catch (err: unknown) {
      console.error('Failed to join lobby:', err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const errorMsg = (err as any).response?.data?.detail || 'Failed to join lobby. Please check the game code and try again.';
      setError(errorMsg);
    } finally {
      setIsJoining(false);
    }
  };

  const handleGameCodeChange = (value: string) => {
    // Only allow alphanumeric characters, max 6
    const cleaned = value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
    setGameCode(cleaned);
  };

  // Codes are always exactly 6 alphanumerics — don't enable Join until then.
  const canJoin = gameCode.trim().length === 6 && !isJoining;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && canJoin) {
      handleJoin();
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
            Join Game
          </h1>
          <p style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink-muted)' }}>
            Enter a game code to join as <span style={{ color: 'var(--you)' }}>{playerName}</span>
          </p>
        </div>

        {/* Form */}
        <div
          style={{
            background: '#241E17',
            borderRadius: '8px',
            border: '1px solid rgba(242,193,78,.25)',
            padding: 'var(--spacing-component-xl)',
          }}
        >
          <div className="content-spacing">
            {/* Game Code Input */}
            <div>
              <label
                htmlFor="game-code-input"
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '.08em',
                  color: 'var(--ink-muted)',
                  marginBottom: 'var(--spacing-component-xs)',
                }}
              >
                Game Code
              </label>
              <input
                id="game-code-input"
                type="text"
                value={gameCode}
                onChange={(e) => handleGameCodeChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="6-character code"
                maxLength={6}
                disabled={isJoining}
                autoFocus
                className="w-full uppercase"
                style={{
                  borderRadius: '6px',
                  background: 'var(--bar, rgba(237,232,222,.06))',
                  border: '1px solid rgba(237,232,222,.25)',
                  fontFamily: 'monospace',
                  fontSize: '26px',
                  fontWeight: 900,
                  textAlign: 'center',
                  letterSpacing: '.25em',
                  color: 'var(--ink-text)',
                  padding: 'var(--spacing-component-md)',
                  opacity: isJoining ? 0.5 : 1,
                  cursor: isJoining ? 'not-allowed' : 'text',
                }}
              />
              <p style={{ fontSize: '11px', color: 'var(--ink-faint)', textAlign: 'center', marginTop: '4px' }}>
                Example: 9P47XA
              </p>
            </div>

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

            {/* Join Button */}
            <button
              onClick={handleJoin}
              disabled={!canJoin}
              style={{
                width: '100%',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 900,
                fontSize: '18px',
                padding: 'var(--spacing-component-md) 0',
                background: canJoin ? 'var(--gold)' : 'rgba(237,232,222,.15)',
                color: canJoin ? 'var(--desk-bottom)' : 'var(--ink-faint)',
                boxShadow: canJoin ? '0 3px 0 rgba(0,0,0,.5)' : 'none',
                cursor: canJoin ? 'pointer' : 'not-allowed',
              }}
            >
              {isJoining ? 'Joining Game...' : 'Join Game'}
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
          <p style={{ fontWeight: 900, fontSize: '13px', color: 'var(--them)', marginBottom: '4px' }}>
            Need a game code?
          </p>
          <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>
            Ask your friend to create a game and share the 6-character code with you.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * PlayersBanner Component
 *
 * Compact banner showing both players in a VS format.
 * Used during deck selection to show who's playing.
 * Viewer-relative identity: the current player renders --you (blue), the
 * other player renders --them (purple).
 */

interface PlayersBannerProps {
  player1Name: string;
  player2Name: string;
  currentPlayerId: 'player1' | 'player2';
}

export function PlayersBanner({
  player1Name,
  player2Name,
  currentPlayerId,
}: PlayersBannerProps) {
  const player1Color = currentPlayerId === 'player1' ? 'var(--you)' : 'var(--them)';
  const player2Color = currentPlayerId === 'player2' ? 'var(--you)' : 'var(--them)';

  return (
    <div
      style={{
        background: 'rgba(180,142,222,.08)',
        borderBottom: '1px solid rgba(180,142,222,.25)',
        padding: 'var(--spacing-component-sm)',
        marginBottom: 'var(--spacing-component-md)',
      }}
    >
      <div
        className="max-w-7xl mx-auto grid grid-cols-[1fr_auto_1fr] items-center"
        style={{ gap: 'var(--spacing-component-lg)' }}
      >
        {/* Player 1 - Right aligned */}
        <div className="text-right">
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--ink-faint)', marginBottom: '4px' }}>
            Player 1
          </div>
          <div style={{ fontWeight: 900, fontSize: '17px', color: player1Color }}>
            {player1Name} {currentPlayerId === 'player1' && <span>(You)</span>}
          </div>
        </div>

        {/* VS divider */}
        <div
          style={{
            fontFamily: 'var(--font-card-name)',
            fontSize: '22px',
            color: 'var(--ink-faint)',
            paddingLeft: 'var(--spacing-component-md)',
            paddingRight: 'var(--spacing-component-md)',
          }}
        >
          vs
        </div>

        {/* Player 2 - Left aligned */}
        <div className="text-left">
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--ink-faint)', marginBottom: '4px' }}>
            Player 2
          </div>
          <div style={{ fontWeight: 900, fontSize: '17px', color: player2Color }}>
            {player2Name} {currentPlayerId === 'player2' && <span>(You)</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

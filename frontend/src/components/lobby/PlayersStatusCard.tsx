/**
 * PlayersStatusCard Component
 *
 * Displays both players' status in a lobby:
 * - Player names with "You" indicator
 * - Ready/waiting states
 * - Deck submission status
 *
 * Viewer-relative identity: the current player renders --you (blue), the
 * other player renders --them (purple).
 */

interface PlayerInfo {
  name: string | null;
  isCurrentPlayer: boolean;
  isReady: boolean;
}

interface PlayersStatusCardProps {
  player1: PlayerInfo;
  player2: PlayerInfo;
}

function PlayerRow({ player, label }: { player: PlayerInfo; label: string }) {
  const nameColor = player.isCurrentPlayer ? 'var(--you)' : 'var(--them)';

  return (
    <div
      className="flex items-center justify-between"
      style={{
        background: 'rgba(237,232,222,.05)',
        borderRadius: '6px',
        padding: 'var(--spacing-component-md)',
      }}
    >
      <div>
        <div style={{ fontWeight: 900, fontSize: '17px', color: player.name ? nameColor : 'var(--ink-faint)' }}>
          {player.name ? (
            <>
              {player.name}
              {player.isCurrentPlayer && (
                <span style={{ marginLeft: 'var(--spacing-component-xs)', color: 'var(--ink-muted)', fontWeight: 700 }}>
                  (You)
                </span>
              )}
            </>
          ) : (
            'Waiting for player...'
          )}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--ink-faint)' }}>{label}</div>
      </div>
      <div>
        {player.isReady && (
          <span style={{ color: 'var(--you)', fontWeight: 700, fontSize: '13px' }}>Deck Ready</span>
        )}
      </div>
    </div>
  );
}

export function PlayersStatusCard({ player1, player2 }: PlayersStatusCardProps) {
  return (
    <div
      style={{
        background: '#241E17',
        borderRadius: '8px',
        border: '1px solid rgba(242,193,78,.25)',
        padding: 'var(--spacing-component-xl)',
      }}
    >
      <h2
        style={{
          fontFamily: 'var(--font-card-name)',
          fontSize: '22px',
          textAlign: 'center',
          marginBottom: 'var(--spacing-component-lg)',
          color: 'var(--ink-text)',
        }}
      >
        Players
      </h2>

      <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
        <PlayerRow player={player1} label="Player 1" />

        <div style={{ textAlign: 'center', color: 'var(--ink-faint)', fontWeight: 700, fontSize: '12px' }}>
          vs
        </div>

        <PlayerRow player={player2} label="Player 2" />
      </div>
    </div>
  );
}

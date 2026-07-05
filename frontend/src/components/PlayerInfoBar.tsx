/**
 * PlayerInfoBar — the score chip (Paper & Ink §7.1).
 *
 * One chip per player, both identical: [name] [hand pip ×n] [broken pip ×n] [⚡n],
 * order fixed. The broken pip is a cracked-card outline and *is the score* — you
 * win when all 6 of the opponent's cards are broken. Chip tint + name color come
 * from whether the player is you (blue) or the opponent (purple), read from
 * LocalPlayerContext. The hand pip uses the player's own material (cream / ink).
 *
 * Values from the signed-off mockup (direction 6a).
 */

import type { Player } from '../types/game';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';

interface PlayerInfoBarProps {
  player: Player;
}

export function PlayerInfoBar({ player }: PlayerInfoBarProps) {
  const localPlayerId = useLocalPlayerId();
  const isOwn = localPlayerId != null && player.player_id === localPlayerId;

  const handCount = player.hand_count ?? player.hand?.length ?? 0;
  const brokenCount = player.break_zone.length;

  const accent = isOwn ? 'var(--you)' : 'var(--them)';
  const chipBg = isOwn ? 'rgba(126,166,224,.08)' : 'rgba(180,142,222,.07)';
  const chipBorder = isOwn ? 'rgba(126,166,224,.3)' : 'rgba(180,142,222,.28)';

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        background: chipBg,
        border: `1px solid ${chipBorder}`,
        borderRadius: '8px',
        padding: '6px 8px',
      }}
    >
      <span style={{ color: accent, fontWeight: 900, fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {player.name}
      </span>

      {/* Hand pip — the player's own card material (cream if you, ink if them). */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', flexShrink: 0 }} title={`${handCount} in hand`}>
        <span
          style={{
            width: '11px',
            height: '15px',
            background: isOwn ? 'var(--paper)' : 'var(--ink)',
            border: isOwn ? undefined : '1px solid rgba(239,231,214,.4)',
            borderRadius: '2px',
          }}
        />
        <span style={{ fontWeight: 900, fontSize: '14px' }}>{handCount}</span>
      </span>

      {/* Broken pip — cracked-card outline; this is the score (win = all 6 broken). */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', flexShrink: 0 }} title={`${brokenCount} broken`}>
        <span
          style={{
            width: '11px',
            height: '15px',
            border: '1.5px solid var(--danger)',
            borderRadius: '2px',
            background: 'linear-gradient(45deg,transparent 44%,var(--danger) 44%,var(--danger) 56%,transparent 56%)',
          }}
        />
        <span style={{ color: 'var(--danger)', fontWeight: 900, fontSize: '14px' }}>{brokenCount}</span>
      </span>

      {/* Charge */}
      <span style={{ color: 'var(--gold)', fontWeight: 900, fontSize: '14px', flexShrink: 0 }} title={`${player.charge} Charge`}>
        ⚡{player.charge}
      </span>
    </div>
  );
}

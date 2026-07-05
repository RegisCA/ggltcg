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
 *
 * `chargeVariant` (design-review only, 2026-07 charge-visibility prototype —
 * see docs/plans/PAPER_AND_INK_PHASE3_HANDOFF.md "next-session candidates"):
 * - 'current' (default everywhere in the real app): unchanged baseline.
 * - 'chargePops': your own charge value gets stronger gold emphasis + a brief
 *   scale pulse when it changes (reduced-motion respected). Opponent unchanged.
 * - 'activeHighlight': the active player's whole chip gets an identity-color
 *   (--you/--them, never --gold) border/background lift; inactive chip dims.
 * - 'both': chargePops + activeHighlight together.
 * The prop always defaults to 'current' so nothing outside the harness changes.
 */

import { motion } from 'framer-motion';
import type { Player } from '../types/game';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';

export type ChargeVisibilityVariant = 'current' | 'chargePops' | 'activeHighlight' | 'both';

interface PlayerInfoBarProps {
  player: Player;
  /** Whether this player is the active (current-turn) player. Only consulted
   *  by the 'activeHighlight'/'both' variants; ignored by 'current'. */
  isActivePlayer?: boolean;
  /** Design-review variant switch — see file header. Defaults to 'current'. */
  chargeVariant?: ChargeVisibilityVariant;
}

export function PlayerInfoBar({ player, isActivePlayer = false, chargeVariant = 'current' }: PlayerInfoBarProps) {
  const localPlayerId = useLocalPlayerId();
  const isOwn = localPlayerId != null && player.player_id === localPlayerId;
  const prefersReducedMotion = useReducedMotion();
  const previousCharge = usePreviousValue(player.charge);

  const handCount = player.hand_count ?? player.hand?.length ?? 0;
  const brokenCount = player.break_zone.length;

  const accent = isOwn ? 'var(--you)' : 'var(--them)';

  const chargePops = chargeVariant === 'chargePops' || chargeVariant === 'both';
  const activeHighlight = chargeVariant === 'activeHighlight' || chargeVariant === 'both';

  const chargeChanged =
    chargePops && isOwn && previousCharge !== undefined && previousCharge !== player.charge;

  // Base chip tint (unchanged from baseline).
  let chipBg = isOwn ? 'rgba(126,166,224,.08)' : 'rgba(180,142,222,.07)';
  let chipBorder = isOwn ? 'rgba(126,166,224,.3)' : 'rgba(180,142,222,.28)';
  let chipOpacity = 1;
  let chipBoxShadow: string | undefined;

  if (activeHighlight) {
    if (isActivePlayer) {
      // Active player: identity-color lift (--you/--them), never --gold —
      // gold stays reserved for charge/action per §2/§7.2.
      chipBg = isOwn ? 'rgba(126,166,224,.16)' : 'rgba(180,142,222,.15)';
      chipBorder = isOwn ? 'var(--you)' : 'var(--them)';
      chipBoxShadow = isOwn
        ? '0 0 0 1px rgba(126,166,224,.25), 0 4px 10px rgba(126,166,224,.18)'
        : '0 0 0 1px rgba(180,142,222,.22), 0 4px 10px rgba(180,142,222,.18)';
    } else {
      chipOpacity = 0.72;
    }
  }

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
        opacity: chipOpacity,
        boxShadow: chipBoxShadow,
        transition: prefersReducedMotion ? undefined : 'background .2s ease, border-color .2s ease, opacity .2s ease, box-shadow .2s ease',
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

      {/* Charge — chargePops variant gives your own value stronger emphasis
          (bigger numeral + gold chip) and a brief pulse on change. */}
      <motion.span
        key={chargePops ? `charge-${player.charge}` : 'charge'}
        style={{
          color: 'var(--gold)',
          fontWeight: 900,
          fontSize: chargePops && isOwn ? '18px' : '14px',
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          borderRadius: '5px',
          padding: chargePops && isOwn ? '1px 6px' : undefined,
          background: chargePops && isOwn ? 'rgba(242,193,78,.16)' : undefined,
          border: chargePops && isOwn ? '1px solid rgba(242,193,78,.5)' : undefined,
        }}
        title={`${player.charge} Charge`}
        initial={false}
        animate={
          !prefersReducedMotion && chargeChanged ? { scale: [1, 1.35, 1] } : { scale: 1 }
        }
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        ⚡{player.charge}
      </motion.span>
    </div>
  );
}

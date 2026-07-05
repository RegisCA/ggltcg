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
 * Charge-visibility treatment (PR #389, from the Phase-3 handoff usability
 * item: your own charge was hard to locate mid-turn — Régis picked variant C
 * of the A/B/C prototype):
 * - Your own charge gets strong gold emphasis: larger numeral in a gold-tinted
 *   chip, plus a brief scale pulse when the value changes (reduced-motion
 *   respected). The opponent's charge stays quiet.
 * - The active player's whole chip gets an identity-color lift (--you/--them
 *   border + glow — never --gold, which stays reserved for charge/action);
 *   the inactive player's chip dims slightly.
 */

import { motion } from 'framer-motion';
import type { Player } from '../types/game';
import { useLocalPlayerId } from '../contexts/LocalPlayerContext';
import { usePreviousValue } from '../hooks/usePreviousValue';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface PlayerInfoBarProps {
  player: Player;
  /** Whether this player is the active (current-turn) player — drives the
   *  identity-color chip highlight / inactive dim. */
  isActivePlayer?: boolean;
}

export function PlayerInfoBar({ player, isActivePlayer = false }: PlayerInfoBarProps) {
  const localPlayerId = useLocalPlayerId();
  const isOwn = localPlayerId != null && player.player_id === localPlayerId;
  const prefersReducedMotion = useReducedMotion();
  const previousCharge = usePreviousValue(player.charge);

  const handCount = player.hand_count ?? player.hand?.length ?? 0;
  const brokenCount = player.break_zone.length;

  const accent = isOwn ? 'var(--you)' : 'var(--them)';

  const chargeChanged = isOwn && previousCharge !== undefined && previousCharge !== player.charge;

  // Active player: identity-color lift (--you/--them), never --gold — gold
  // stays reserved for charge/action per §2/§7.2. Inactive player dims.
  const chipBg = isActivePlayer
    ? isOwn ? 'rgba(126,166,224,.16)' : 'rgba(180,142,222,.15)'
    : isOwn ? 'rgba(126,166,224,.08)' : 'rgba(180,142,222,.07)';
  const chipBorder = isActivePlayer
    ? isOwn ? 'var(--you)' : 'var(--them)'
    : isOwn ? 'rgba(126,166,224,.3)' : 'rgba(180,142,222,.28)';
  const chipBoxShadow = isActivePlayer
    ? isOwn
      ? '0 0 0 1px rgba(126,166,224,.25), 0 4px 10px rgba(126,166,224,.18)'
      : '0 0 0 1px rgba(180,142,222,.22), 0 4px 10px rgba(180,142,222,.18)'
    : undefined;
  const chipOpacity = isActivePlayer ? 1 : 0.72;

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

      {/* Charge — your own value gets stronger emphasis (bigger numeral in a
          gold chip) and a brief pulse on change; opponent's stays quiet. */}
      <motion.span
        key={`charge-${player.charge}`}
        style={{
          color: 'var(--gold)',
          fontWeight: 900,
          fontSize: isOwn ? '18px' : '14px',
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          borderRadius: '5px',
          padding: isOwn ? '1px 6px' : undefined,
          background: isOwn ? 'rgba(242,193,78,.16)' : undefined,
          border: isOwn ? '1px solid rgba(242,193,78,.5)' : undefined,
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

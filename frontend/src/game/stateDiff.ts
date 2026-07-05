/**
 * Pure game-state differ.
 *
 * `diffGameStates(prev, next)` compares two GameState snapshots and produces
 * an ordered list of semantic events describing what changed between them.
 * This is the foundation for a board-animation / event-feedback layer — it
 * has no React imports and no side effects, and must never throw on any
 * pair of well-formed GameStates.
 *
 * ## Card visibility & hidden-hand inference
 *
 * `Player.hand` is `Card[] | null`: an opponent's hand is hidden (`null`)
 * while your own hand (and any hand you can otherwise see) is a real array.
 * Cards are indexed by their globally-unique `id` across every visible zone
 * (both players' `hand` when present, `in_play`, and `break_zone`) in each
 * snapshot. A card's "location" is `{ playerId, zone }` — the player whose
 * list it currently sits in (the *controller's* list for `in_play`/`break`,
 * since a stolen card sits in the thief's `in_play`), not necessarily its
 * `owner`.
 *
 * When a card can't be located in one of the two snapshots because it sits
 * in a hidden hand, we infer a hand-boundary move:
 *   - Visible only in `next` -> it came from a hidden hand: emit
 *     `card_moved` with `from = { playerId: card.owner, zone: 'hand' }`.
 *   - Visible only in `prev` -> it returned to a hidden hand (e.g. a
 *     "return to hand" effect like Toynado): emit `card_moved` with
 *     `to = { playerId: card.owner, zone: 'hand' }`.
 *   - Invisible in both, or visible in both with no resolvable zone change
 *     (e.g. our own hidden-hand toggling on/off between snapshots with no
 *     other information) -> emit nothing; we can't claim a real move
 *     happened.
 *
 * ## Event semantics
 *
 * - `card_moved`: the card is located in both snapshots (directly or via
 *   hidden-hand inference) and its zone differs, OR the list-owner differs
 *   *because* the zone changed (e.g. a stolen card's owner reclaims it on
 *   break: thief's `in_play` -> owner's `break`). A location change where
 *   only the controller differs but the zone stays `in_play` is NOT a
 *   `card_moved` — see `control_changed`.
 * - `control_changed`: the card stays in `in_play` in both snapshots, but
 *   its `controller` field differs (e.g. Twist). This changes which
 *   player's list holds it, but since the zone itself didn't change we
 *   emit only `control_changed`, never a `card_moved`.
 * - `stat_changed`: one event per stat (`speed`, `strength`, `stamina`,
 *   `current_stamina`, `effective_cost`) that changed, only for cards that
 *   are located in `in_play` in both snapshots. `null` vs a number counts
 *   as a change.
 * - `charge_changed` / `hand_count_changed`: per-player charge/hand_count
 *   deltas. `hand_count` is used (not `hand.length`) so it works even when
 *   the hand is hidden.
 * - `turn_changed`: `turn_number` differs.
 * - `game_over`: `is_game_over` flips to true (uses `winner`).
 *
 * ## Emission order (stable, documented)
 *
 * 1. `turn_changed` (at most one)
 * 2. `charge_changed` / `hand_count_changed`, interleaved per player in
 *    `Object.keys(next.players)` order (charge before hand_count for a
 *    given player)
 * 3. `card_moved` (in the order cards are first encountered while walking
 *    `next`'s zones: hand, in_play, break_zone, per player in key order;
 *    hand-boundary "returned to hand" moves — visible only in prev — are
 *    appended after that walk, in `prev` zone-walk order)
 * 4. `control_changed`
 * 5. `stat_changed`
 * 6. `game_over` (at most one, last)
 *
 * Identical snapshots produce `[]`.
 */

import type { Card, GameState, Player } from '../types/game';

export type ZoneName = 'hand' | 'in_play' | 'break';

export interface ZoneRef {
  playerId: string;
  zone: ZoneName;
}

export type GameStateEvent =
  | { type: 'card_moved'; cardId: string; cardName: string; from: ZoneRef; to: ZoneRef }
  | { type: 'control_changed'; cardId: string; cardName: string; fromPlayerId: string; toPlayerId: string }
  | {
      type: 'stat_changed';
      cardId: string;
      cardName: string;
      stat: 'speed' | 'strength' | 'stamina' | 'current_stamina' | 'effective_cost';
      from: number | null;
      to: number | null;
    }
  | { type: 'charge_changed'; playerId: string; from: number; to: number }
  | { type: 'hand_count_changed'; playerId: string; from: number; to: number }
  | { type: 'turn_changed'; fromTurn: number; toTurn: number; activePlayerId: string }
  | { type: 'game_over'; winnerId: string };

const STAT_KEYS = ['speed', 'strength', 'stamina', 'current_stamina', 'effective_cost'] as const;

interface Located {
  card: Card;
  location: ZoneRef;
}

/**
 * Build a map of cardId -> { card, location } for every card visible in a
 * snapshot, walking players in object-key order, and within a player:
 * hand, in_play, break_zone.
 */
function indexVisibleCards(state: GameState): Map<string, Located> {
  const index = new Map<string, Located>();

  const zonesInOrder: Array<[ZoneName, (p: Player) => Card[] | null]> = [
    ['hand', (p) => p.hand],
    ['in_play', (p) => p.in_play],
    ['break', (p) => p.break_zone],
  ];

  for (const [playerId, player] of Object.entries(state.players ?? {})) {
    for (const [zone, getList] of zonesInOrder) {
      const list = getList(player);
      if (!list) continue; // hidden hand
      for (const card of list) {
        if (!card || !card.id) continue;
        // First writer wins in the (unlikely) case of a duplicate id.
        if (!index.has(card.id)) {
          index.set(card.id, { card, location: { playerId, zone } });
        }
      }
    }
  }

  return index;
}

function sameZoneRef(a: ZoneRef, b: ZoneRef): boolean {
  return a.playerId === b.playerId && a.zone === b.zone;
}

export function diffGameStates(prev: GameState, next: GameState): GameStateEvent[] {
  const events: GameStateEvent[] = [];

  if (!prev || !next) return events;

  // 1. turn_changed
  if (prev.turn_number !== next.turn_number) {
    events.push({
      type: 'turn_changed',
      fromTurn: prev.turn_number,
      toTurn: next.turn_number,
      activePlayerId: next.active_player_id,
    });
  }

  // 2. charge_changed / hand_count_changed, per player in next's key order
  const prevPlayers = prev.players ?? {};
  const nextPlayers = next.players ?? {};

  for (const [playerId, nextPlayer] of Object.entries(nextPlayers)) {
    const prevPlayer = prevPlayers[playerId];
    if (!prevPlayer) continue;

    if (prevPlayer.charge !== nextPlayer.charge) {
      events.push({
        type: 'charge_changed',
        playerId,
        from: prevPlayer.charge,
        to: nextPlayer.charge,
      });
    }

    if (prevPlayer.hand_count !== nextPlayer.hand_count) {
      events.push({
        type: 'hand_count_changed',
        playerId,
        from: prevPlayer.hand_count,
        to: nextPlayer.hand_count,
      });
    }
  }

  // Build visibility indexes.
  const prevIndex = indexVisibleCards(prev);
  const nextIndex = indexVisibleCards(next);

  const cardMovedEvents: GameStateEvent[] = [];
  const controlChangedEvents: GameStateEvent[] = [];
  const statChangedEvents: GameStateEvent[] = [];

  const handledForMove = new Set<string>();

  // 3a. Walk next's visible cards (in insertion/zone-walk order) to find
  // moves and control changes for cards visible in next.
  for (const [cardId, nextLoc] of nextIndex) {
    const prevLoc = prevIndex.get(cardId);

    if (!prevLoc) {
      // Visible only in next -> came from a hidden hand.
      const owner = nextLoc.card.owner;
      cardMovedEvents.push({
        type: 'card_moved',
        cardId,
        cardName: nextLoc.card.name,
        from: { playerId: owner, zone: 'hand' },
        to: nextLoc.location,
      });
      handledForMove.add(cardId);
      continue;
    }

    handledForMove.add(cardId);

    const zoneChanged = prevLoc.location.zone !== nextLoc.location.zone;
    const ownerListChanged = !sameZoneRef(prevLoc.location, nextLoc.location);

    if (zoneChanged) {
      cardMovedEvents.push({
        type: 'card_moved',
        cardId,
        cardName: nextLoc.card.name,
        from: prevLoc.location,
        to: nextLoc.location,
      });
    } else if (ownerListChanged) {
      // Same zone (in_play/in_play or break/break), different list-owner:
      // this is a controller change while the zone itself is unchanged.
      if (nextLoc.location.zone === 'in_play' && prevLoc.card.controller !== nextLoc.card.controller) {
        controlChangedEvents.push({
          type: 'control_changed',
          cardId,
          cardName: nextLoc.card.name,
          fromPlayerId: prevLoc.location.playerId,
          toPlayerId: nextLoc.location.playerId,
        });
      }
      // (break/break owner-list changes without a zone change aren't part
      // of the documented contract; nothing else to do here.)
    } else if (
      nextLoc.location.zone === 'in_play' &&
      prevLoc.card.controller !== nextLoc.card.controller
    ) {
      // Same list, but controller field itself flipped (shouldn't normally
      // happen without also changing which list holds it, but guard anyway).
      controlChangedEvents.push({
        type: 'control_changed',
        cardId,
        cardName: nextLoc.card.name,
        fromPlayerId: prevLoc.card.controller,
        toPlayerId: nextLoc.card.controller,
      });
    }

    // stat_changed: only for cards in play in both snapshots.
    if (prevLoc.location.zone === 'in_play' && nextLoc.location.zone === 'in_play') {
      for (const stat of STAT_KEYS) {
        const fromVal = prevLoc.card[stat];
        const toVal = nextLoc.card[stat];
        if (fromVal !== toVal) {
          statChangedEvents.push({
            type: 'stat_changed',
            cardId,
            cardName: nextLoc.card.name,
            stat,
            from: fromVal,
            to: toVal,
          });
        }
      }
    }
  }

  // 3b. Cards visible only in prev -> returned to a hidden hand.
  for (const [cardId, prevLoc] of prevIndex) {
    if (handledForMove.has(cardId)) continue;
    if (nextIndex.has(cardId)) continue; // shouldn't happen, but be safe

    const owner = prevLoc.card.owner;
    cardMovedEvents.push({
      type: 'card_moved',
      cardId,
      cardName: prevLoc.card.name,
      from: prevLoc.location,
      to: { playerId: owner, zone: 'hand' },
    });
  }

  events.push(...cardMovedEvents, ...controlChangedEvents, ...statChangedEvents);

  // 6. game_over last
  if (!prev.is_game_over && next.is_game_over && next.winner) {
    events.push({ type: 'game_over', winnerId: next.winner });
  }

  return events;
}

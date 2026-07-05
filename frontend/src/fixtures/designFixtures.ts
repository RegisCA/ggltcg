/**
 * Design Preview Fixtures
 *
 * Canned game states for the /design.html design-preview harness.
 * Each fixture is a frozen, backend-free GameState + valid actions pair that
 * GameBoard can render exactly as it would a live game.
 *
 * Card data mirrors backend/data/cards.csv (names, costs, stats, colors) so
 * previews look like real play. Instance IDs are hand-assigned and stable.
 *
 * gameService intercepts any gameId starting with `fixture-` and serves these
 * instead of calling the API (see src/api/gameService.ts). This module is
 * lazy-imported there, so it stays out of the main bundle for normal players.
 */

import type { Card, CardType, GameState, PlayByPlayEntry, Player, ValidAction, Zone } from '../types/game';
import type { ActionResponse, ValidActionsResponse } from '../types/api';

export const FIXTURE_HUMAN_ID = 'fixture-you';
export const FIXTURE_AI_ID = 'fixture-opponent';

/** Response returned for any action attempted against a fixture game. */
export const FIXTURE_ACTION_RESPONSE: ActionResponse = {
  success: true,
  message: 'Design preview: actions are display-only',
};

// ============================================================================
// CARD DEFINITIONS (subset of backend/data/cards.csv)
// ============================================================================

interface CardDef {
  card_type: CardType;
  cost: number;
  effect_text: string;
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  primary_color: string;
  accent_color: string;
}

const toy = (
  cost: number,
  effect_text: string,
  speed: number,
  strength: number,
  stamina: number,
  primary_color: string,
  accent_color = primary_color
): CardDef => ({ card_type: 'Toy', cost, effect_text, speed, strength, stamina, primary_color, accent_color });

const action = (
  cost: number,
  effect_text: string,
  primary_color: string,
  accent_color = primary_color
): CardDef => ({
  card_type: 'Action',
  cost,
  effect_text,
  speed: null,
  strength: null,
  stamina: null,
  primary_color,
  accent_color,
});

const DEFS: Record<string, CardDef> = {
  Beary: toy(1, "Your opponent's cards' effects don't affect this card.", 5, 3, 3, '#C74444'),
  Knight: toy(1, 'On your turn, this card wins all tussles it enters.', 4, 4, 3, '#C74444'),
  Archer: toy(0, "This card can't start tussles. You may spend Charge to remove stamina from cards.", 0, 0, 5, '#C74444'),
  Umbruh: toy(1, 'When broken, gain 1 Charge.', 4, 4, 4, '#C74444'),
  Ka: toy(2, 'Your cards have + 2 strength.', 5, 9, 1, '#C74444'),
  Ballaber: toy(3, 'You may break 1 of your cards to play this card for free.', 4, 6, 4, '#C74444'),
  Drum: toy(1, 'Your cards have 2 more speed.', 1, 3, 2, '#eb9113'),
  Violin: toy(1, 'Your cards have 2 more strength.', 3, 1, 2, '#eb9113'),
  Gibbers: toy(1, "Your opponent's cards cost 1 more.", 1, 1, 1, '#eb9113'),
  Belchaletta: toy(1, 'At the start of your turn, gain 2 Charge.', 3, 3, 4, '#eb9113'),
  'Hind Leg Kicker': toy(1, 'When you play a card (not this one), gain 1 Charge.', 3, 3, 1, '#eb9113'),
  'Sock Sorcerer': toy(3, "Your opponent's cards' effects don't affect your cards.", 3, 3, 5, '#eb9113'),
  'Bubble Blocker': toy(0, "Your opponent's cards' effects don't affect your cards.", 2, 2, 1, '#87CEEB'),
  'Paper Plane': toy(1, 'This card can direct attack even if your opponent has cards in play.', 2, 2, 1, '#87CEEB', '#4682B4'),
  Stomp: action(-1, 'You may break a card that is in play.', '#FFB6C1'),
  Drop: action(2, 'Break a card that is in play.', '#e612d0'),
  Jumpscare: action(0, 'Put a card that is in play into their owner\'s hand.', '#e612d0'),
  Surge: action(0, 'Gain 1 Charge.', '#e612d0'),
  Rush: action(0, 'Gain 2 Charge. This card may not be played on your first turn.', '#ffeb99', '#ffa51f'),
  Wake: action(1, 'Fix 1 of your cards.', '#8B5FA8'),
  Sun: action(3, 'Fix 2 of your cards.', '#8B5FA8'),
  Toynado: action(2, "Put all cards that are in play into their owner's hands.", '#8B5FA8'),
  VeryVeryAppleJuice: action(0, 'This turn, your cards have 1 more of each stat.', '#e612d0'),
};

function makeCard(defName: string, id: string, owner: string, zone: Zone, overrides: Partial<Card> = {}): Card {
  const def = DEFS[defName];
  if (!def) throw new Error(`Unknown fixture card definition: ${defName}`);
  return {
    id,
    name: defName,
    card_type: def.card_type,
    cost: def.cost,
    effective_cost: null,
    effect_text: def.effect_text,
    zone,
    owner,
    controller: owner,
    speed: def.speed,
    strength: def.strength,
    stamina: def.stamina,
    current_stamina: def.stamina,
    base_speed: def.speed,
    base_strength: def.strength,
    base_stamina: def.stamina,
    is_broken: zone === 'Break',
    primary_color: def.primary_color,
    accent_color: def.accent_color,
    ...overrides,
  };
}

function makePlayer(
  playerId: string,
  name: string,
  charge: number,
  zones: { hand?: Card[]; in_play?: Card[]; break_zone?: Card[]; hand_count?: number }
): Player {
  return {
    player_id: playerId,
    name,
    charge,
    hand_count: zones.hand_count ?? zones.hand?.length ?? 0,
    hand: zones.hand ?? null,
    in_play: zones.in_play ?? [],
    break_zone: zones.break_zone ?? [],
    direct_attacks_this_turn: 0,
  };
}

// ============================================================================
// FIXTURES
// ============================================================================

export interface DesignFixture {
  id: string;
  label: string;
  description: string;
  state: GameState;
  validActions: ValidAction[];
}

function playAction(card: Card, extras: Partial<ValidAction> = {}): ValidAction {
  const cost = card.effective_cost ?? card.cost;
  return {
    action_type: 'play_card',
    card_id: card.id,
    card_name: card.name,
    cost_charge: Math.max(cost, 0),
    description: `Play ${card.name} (Cost: ${Math.max(cost, 0)})`,
    ...extras,
  };
}

function tussleAction(attacker: Card, defender: Card | 'direct_attack', cost = 2): ValidAction {
  const targetLabel = defender === 'direct_attack' ? 'Direct attack' : `vs ${defender.name}`;
  return {
    action_type: 'tussle',
    card_id: attacker.id,
    card_name: attacker.name,
    target_options: [defender === 'direct_attack' ? 'direct_attack' : defender.id],
    min_targets: 1,
    max_targets: 1,
    cost_charge: cost,
    description: `Tussle: ${attacker.name} ${targetLabel} (Cost: ${cost})`,
  };
}

const END_TURN: ValidAction = {
  action_type: 'end_turn',
  description: 'End Turn',
};

// ---------------------------------------------------------------------------
// Fixture 1: Opening hand — turn 1, nothing in play yet
// ---------------------------------------------------------------------------

function buildOpening(): DesignFixture {
  const hand = [
    makeCard('Beary', 'fx1-h1', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Rush', 'fx1-h2', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Hind Leg Kicker', 'fx1-h3', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Bubble Blocker', 'fx1-h4', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Stomp', 'fx1-h5', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Archer', 'fx1-h6', FIXTURE_HUMAN_ID, 'Hand'),
  ];
  const [beary, , hindLegKicker, bubbleBlocker, , archer] = hand;

  return {
    id: 'fixture-opening',
    label: 'Opening hand',
    description: 'Turn 1, your turn: full 6-card hand, empty boards.',
    state: {
      game_id: 'fixture-opening',
      turn_number: 1,
      phase: 'Main',
      active_player_id: FIXTURE_HUMAN_ID,
      first_player_id: FIXTURE_HUMAN_ID,
      players: {
        [FIXTURE_HUMAN_ID]: makePlayer(FIXTURE_HUMAN_ID, 'You', 2, { hand }),
        [FIXTURE_AI_ID]: makePlayer(FIXTURE_AI_ID, 'Gemiknight', 0, { hand_count: 6 }),
      },
      winner: null,
      is_game_over: false,
      play_by_play: [],
    },
    validActions: [
      END_TURN,
      playAction(beary),
      playAction(hindLegKicker),
      playAction(bubbleBlocker),
      playAction(archer),
    ],
  };
}

// ---------------------------------------------------------------------------
// Fixture 2: Mid-game — both boards populated, buffs, tussles, targeted plays
// ---------------------------------------------------------------------------

function buildMidgame(): DesignFixture {
  // Your board: Knight (damaged, speed-buffed by Drum) + Drum
  const knight = makeCard('Knight', 'fx2-p1', FIXTURE_HUMAN_ID, 'InPlay', {
    speed: 6, // base 4, +2 from Drum
    current_stamina: 1, // took damage in an earlier tussle
  });
  const drum = makeCard('Drum', 'fx2-p2', FIXTURE_HUMAN_ID, 'InPlay', { speed: 3 });
  const umbruhBroken = makeCard('Umbruh', 'fx2-b1', FIXTURE_HUMAN_ID, 'Break');

  // Opponent board: Ka (fragile powerhouse) + Gibbers (strength-buffed by Ka)
  const ka = makeCard('Ka', 'fx2-o1', FIXTURE_AI_ID, 'InPlay', { current_stamina: 1 });
  const gibbers = makeCard('Gibbers', 'fx2-o2', FIXTURE_AI_ID, 'InPlay', { strength: 3 });
  const opponentBroken = [
    makeCard('Bubble Blocker', 'fx2-ob1', FIXTURE_AI_ID, 'Break'),
    makeCard('Jumpscare', 'fx2-ob2', FIXTURE_AI_ID, 'Break'),
  ];

  const hand = [
    makeCard('Wake', 'fx2-h1', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Drop', 'fx2-h2', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Ballaber', 'fx2-h3', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Surge', 'fx2-h4', FIXTURE_HUMAN_ID, 'Hand'),
  ];
  const [wake, drop, ballaber, surge] = hand;

  return {
    id: 'fixture-midgame',
    label: 'Mid-game',
    description:
      'Turn 5, your turn: cards on both boards, damaged/buffed stats, tussles available. Click Drop for a both-sides target modal; Ballaber shows alternative cost.',
    state: {
      game_id: 'fixture-midgame',
      turn_number: 5,
      phase: 'Main',
      active_player_id: FIXTURE_HUMAN_ID,
      first_player_id: FIXTURE_HUMAN_ID,
      players: {
        [FIXTURE_HUMAN_ID]: makePlayer(FIXTURE_HUMAN_ID, 'You', 3, {
          hand,
          in_play: [knight, drum],
          break_zone: [umbruhBroken],
        }),
        [FIXTURE_AI_ID]: makePlayer(FIXTURE_AI_ID, 'Gemiknight', 1, {
          hand_count: 3,
          in_play: [ka, gibbers],
          break_zone: opponentBroken,
        }),
      },
      winner: null,
      is_game_over: false,
      play_by_play: [
        { turn: 4, player: 'Gemiknight', action_type: 'play_card', description: 'Played Ka (2 Charge)' },
        { turn: 4, player: 'Gemiknight', action_type: 'tussle', description: 'Ka tussled Umbruh (2 Charge)' },
        { turn: 4, player: 'Gemiknight', action_type: 'end_turn', description: 'Ended turn' },
        { turn: 5, player: 'You', action_type: 'draw', description: 'Drew Surge' },
      ],
    },
    validActions: [
      END_TURN,
      playAction(wake, {
        target_options: [umbruhBroken.id],
        min_targets: 1,
        max_targets: 1,
      }),
      playAction(drop, {
        target_options: [knight.id, drum.id, ka.id, gibbers.id],
        min_targets: 1,
        max_targets: 1,
      }),
      playAction(ballaber, {
        alternative_cost_available: true,
        alternative_cost_options: [knight.id, drum.id],
      }),
      playAction(surge),
      tussleAction(knight, ka),
      tussleAction(knight, gibbers),
      tussleAction(drum, ka),
      tussleAction(drum, gibbers),
    ],
  };
}

// ---------------------------------------------------------------------------
// Fixture 3: Break-zone pileup — the confirmed stacking bug (WP-1 #2, WP-2 #8)
// ---------------------------------------------------------------------------

function buildBreakZonePileup(): DesignFixture {
  const beary = makeCard('Beary', 'fx3-p1', FIXTURE_HUMAN_ID, 'InPlay', { current_stamina: 2 });
  const sockSorcerer = makeCard('Sock Sorcerer', 'fx3-o1', FIXTURE_AI_ID, 'InPlay');

  const humanBreak = [
    makeCard('Umbruh', 'fx3-b1', FIXTURE_HUMAN_ID, 'Break'),
    makeCard('Knight', 'fx3-b2', FIXTURE_HUMAN_ID, 'Break'),
    makeCard('Violin', 'fx3-b3', FIXTURE_HUMAN_ID, 'Break'),
    makeCard('Surge', 'fx3-b4', FIXTURE_HUMAN_ID, 'Break'),
    makeCard('Hind Leg Kicker', 'fx3-b5', FIXTURE_HUMAN_ID, 'Break'),
  ];
  const opponentBreak = [
    makeCard('Ka', 'fx3-ob1', FIXTURE_AI_ID, 'Break'),
    makeCard('Gibbers', 'fx3-ob2', FIXTURE_AI_ID, 'Break'),
    makeCard('Drop', 'fx3-ob3', FIXTURE_AI_ID, 'Break'),
  ];

  const hand = [
    makeCard('Wake', 'fx3-h1', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Sun', 'fx3-h2', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Toynado', 'fx3-h3', FIXTURE_HUMAN_ID, 'Hand'),
  ];
  const [wake, sun, toynado] = hand;

  // Only Toy cards can be fixed back into play
  const fixableIds = [humanBreak[0].id, humanBreak[1].id, humanBreak[2].id, humanBreak[4].id];

  return {
    id: 'fixture-breakzones',
    label: 'Break-zone pileup',
    description: 'Turn 9, your turn: 5 broken cards vs 3 — the stacking-bug state. Wake/Sun target the break zone.',
    state: {
      game_id: 'fixture-breakzones',
      turn_number: 9,
      phase: 'Main',
      active_player_id: FIXTURE_HUMAN_ID,
      first_player_id: FIXTURE_HUMAN_ID,
      players: {
        [FIXTURE_HUMAN_ID]: makePlayer(FIXTURE_HUMAN_ID, 'You', 4, {
          hand,
          in_play: [beary],
          break_zone: humanBreak,
        }),
        [FIXTURE_AI_ID]: makePlayer(FIXTURE_AI_ID, 'Gemiknight', 2, {
          hand_count: 2,
          in_play: [sockSorcerer],
          break_zone: opponentBreak,
        }),
      },
      winner: null,
      is_game_over: false,
      play_by_play: [
        { turn: 8, player: 'Gemiknight', action_type: 'tussle', description: 'Sock Sorcerer tussled Violin (2 Charge)' },
        { turn: 8, player: 'Gemiknight', action_type: 'end_turn', description: 'Ended turn' },
        { turn: 9, player: 'You', action_type: 'draw', description: 'Drew Toynado' },
      ],
    },
    validActions: [
      END_TURN,
      playAction(wake, { target_options: fixableIds, min_targets: 1, max_targets: 1 }),
      playAction(sun, { target_options: fixableIds, min_targets: 1, max_targets: 2 }),
      playAction(toynado),
      tussleAction(beary, sockSorcerer),
    ],
  };
}

// ---------------------------------------------------------------------------
// Fixture 4: Opponent's turn — the "AI is thinking" dead air (WP-1 #3)
// ---------------------------------------------------------------------------

function buildOpponentTurn(): DesignFixture {
  const knight = makeCard('Knight', 'fx4-p1', FIXTURE_HUMAN_ID, 'InPlay', { speed: 6, current_stamina: 1 });
  const drum = makeCard('Drum', 'fx4-p2', FIXTURE_HUMAN_ID, 'InPlay', { speed: 3 });
  const ka = makeCard('Ka', 'fx4-o1', FIXTURE_AI_ID, 'InPlay', { current_stamina: 1 });
  const belchaletta = makeCard('Belchaletta', 'fx4-o2', FIXTURE_AI_ID, 'InPlay');

  const hand = [
    makeCard('Wake', 'fx4-h1', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Drop', 'fx4-h2', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Ballaber', 'fx4-h3', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('Surge', 'fx4-h4', FIXTURE_HUMAN_ID, 'Hand'),
    makeCard('VeryVeryAppleJuice', 'fx4-h5', FIXTURE_HUMAN_ID, 'Hand'),
  ];

  return {
    id: 'fixture-opponent-turn',
    label: "Opponent's turn",
    description: "Turn 6, opponent's turn: the persistent 'AI is thinking' state — the playback gap under redesign.",
    state: {
      game_id: 'fixture-opponent-turn',
      turn_number: 6,
      phase: 'Main',
      active_player_id: FIXTURE_AI_ID,
      first_player_id: FIXTURE_HUMAN_ID,
      players: {
        [FIXTURE_HUMAN_ID]: makePlayer(FIXTURE_HUMAN_ID, 'You', 2, {
          hand,
          in_play: [knight, drum],
          break_zone: [makeCard('Umbruh', 'fx4-b1', FIXTURE_HUMAN_ID, 'Break')],
        }),
        [FIXTURE_AI_ID]: makePlayer(FIXTURE_AI_ID, 'Gemiknight', 3, {
          hand_count: 3,
          in_play: [ka, belchaletta],
          break_zone: [makeCard('Bubble Blocker', 'fx4-ob1', FIXTURE_AI_ID, 'Break')],
        }),
      },
      winner: null,
      is_game_over: false,
      play_by_play: [
        // Turn 6 entries arrive via OPPONENT_TURN_SCRIPT (strategy first,
        // then actions), matching the backend's live ordering
        { turn: 5, player: 'You', action_type: 'play_card', description: 'Played Drum (1 Charge)' },
        { turn: 5, player: 'You', action_type: 'tussle', description: 'Knight tussled Gibbers (2 Charge)' },
        { turn: 5, player: 'You', action_type: 'end_turn', description: 'Ended turn' },
      ],
    },
    validActions: [],
  };
}

// ============================================================================
// REGISTRY + LOOKUP API (consumed by gameService and DesignPreview)
// ============================================================================

export const DESIGN_FIXTURES: DesignFixture[] = [
  buildOpening(),
  buildMidgame(),
  buildBreakZonePileup(),
  buildOpponentTurn(),
];

const fixturesById = new Map(DESIGN_FIXTURES.map((f) => [f.id, f]));

// ============================================================================
// SCRIPTED OPPONENT-TURN LOG DRIP
// ============================================================================

/**
 * While the opponent-turn fixture sits in its permanent "thinking" state,
 * reveal these log entries one at a time over the 2s state poll — the live
 * condition where entries land mid-AI-turn and the log must not resize the
 * board around them. Log-only: the board state stays frozen, so the
 * descriptions are written to not contradict the visible board. Also the
 * staging ground for live opponent-turn playback (WP-1 #3, WP-2 #9).
 */
const OPPONENT_TURN_SCRIPT: PlayByPlayEntry[] = [
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'strategy',
    description:
      'Bank Charge with Belchaletta, then trade Ka into Knight to blunt the counter-attack and pressure Drum with what remains.',
  },
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'play_card',
    description: 'Played Belchaletta (1 Charge)',
  },
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'activate_ability',
    description: 'Belchaletta generated 2 Charge',
  },
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'tussle',
    description: 'Ka tussled Knight (2 Charge)',
  },
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'tussle',
    description: 'Belchaletta tussled Drum (2 Charge)',
  },
  {
    turn: 6,
    player: 'Gemiknight',
    action_type: 'end_turn',
    description: 'Ended turn',
  },
];

const SCRIPT_REVEAL_MS = 4000;
const scriptClocks = new Map<string, number>();

export function getFixtureGameState(gameId: string): GameState {
  const fixture = fixturesById.get(gameId);
  if (!fixture) throw new Error(`Unknown design fixture: ${gameId}`);
  if (gameId === 'fixture-opponent-turn') {
    if (!scriptClocks.has(gameId)) scriptClocks.set(gameId, Date.now());
    const elapsed = Date.now() - scriptClocks.get(gameId)!;
    const revealed = Math.min(OPPONENT_TURN_SCRIPT.length, Math.floor(elapsed / SCRIPT_REVEAL_MS));
    if (revealed > 0) {
      return {
        ...fixture.state,
        play_by_play: [...(fixture.state.play_by_play ?? []), ...OPPONENT_TURN_SCRIPT.slice(0, revealed)],
      };
    }
  }
  return fixture.state;
}

export function getFixtureValidActions(gameId: string, playerId: string): ValidActionsResponse {
  const fixture = fixturesById.get(gameId);
  if (!fixture) throw new Error(`Unknown design fixture: ${gameId}`);
  return {
    game_id: gameId,
    player_id: playerId,
    valid_actions: playerId === FIXTURE_HUMAN_ID ? fixture.validActions : [],
  };
}

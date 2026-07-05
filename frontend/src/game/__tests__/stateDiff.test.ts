import { describe, expect, it } from 'vitest';
import { diffGameStates } from '../stateDiff';
import type { Card, GameState, Player } from '../../types/game';

function makeCard(overrides: Partial<Card> & { id: string; name: string; owner: string }): Card {
  return {
    card_type: 'Toy',
    cost: 3,
    effective_cost: null,
    effect_text: '',
    zone: 'InPlay',
    controller: overrides.owner,
    speed: 2,
    strength: 2,
    stamina: 2,
    current_stamina: 2,
    base_speed: 2,
    base_strength: 2,
    base_stamina: 2,
    is_broken: false,
    primary_color: '#fff',
    accent_color: '#000',
    ...overrides,
  };
}

function makePlayer(overrides: Partial<Player> & { player_id: string }): Player {
  return {
    name: overrides.player_id,
    charge: 5,
    hand_count: 0,
    hand: [],
    in_play: [],
    break_zone: [],
    direct_attacks_this_turn: 0,
    ...overrides,
  };
}

function makeState(overrides: Partial<GameState> & { players: Record<string, Player> }): GameState {
  return {
    game_id: 'g1',
    turn_number: 1,
    phase: 'Main',
    active_player_id: 'p1',
    first_player_id: 'p1',
    winner: null,
    is_game_over: false,
    ...overrides,
  };
}

function baseState(): GameState {
  return makeState({
    players: {
      p1: makePlayer({ player_id: 'p1', hand_count: 2, hand: [] }),
      p2: makePlayer({ player_id: 'p2', hand_count: 2, hand: [] }),
    },
  });
}

describe('diffGameStates', () => {
  it('returns [] for identical snapshots', () => {
    const s = baseState();
    expect(diffGameStates(s, s)).toEqual([]);
  });

  it('detects a card played from a visible hand into play', () => {
    const card = makeCard({ id: 'c1', name: 'Bloop', owner: 'p1' });
    const prev = baseState();
    prev.players.p1.hand = [card];
    prev.players.p1.hand_count = 1;

    const next = baseState();
    next.players.p1.hand = [];
    next.players.p1.hand_count = 0;
    next.players.p1.in_play = [{ ...card, zone: 'InPlay' }];

    const events = diffGameStates(prev, next);
    const moved = events.find((e) => e.type === 'card_moved');
    expect(moved).toEqual({
      type: 'card_moved',
      cardId: 'c1',
      cardName: 'Bloop',
      from: { playerId: 'p1', zone: 'hand' },
      to: { playerId: 'p1', zone: 'in_play' },
    });
    expect(events.some((e) => e.type === 'hand_count_changed')).toBe(true);
  });

  it('detects a card played from a hidden opponent hand', () => {
    const prev = baseState();
    prev.players.p2.hand = null;
    prev.players.p2.hand_count = 3;

    const card = makeCard({ id: 'c2', name: 'Zap', owner: 'p2' });
    const next = baseState();
    next.players.p2.hand = null;
    next.players.p2.hand_count = 2;
    next.players.p2.in_play = [card];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'card_moved',
      cardId: 'c2',
      cardName: 'Zap',
      from: { playerId: 'p2', zone: 'hand' },
      to: { playerId: 'p2', zone: 'in_play' },
    });
  });

  it('detects a card broken from play', () => {
    const card = makeCard({ id: 'c3', name: 'Fizz', owner: 'p1' });
    const prev = baseState();
    prev.players.p1.in_play = [card];

    const next = baseState();
    next.players.p1.in_play = [];
    next.players.p1.break_zone = [{ ...card, zone: 'Break', is_broken: true, current_stamina: 0 }];

    const events = diffGameStates(prev, next);
    const moved = events.filter((e) => e.type === 'card_moved');
    expect(moved).toHaveLength(1);
    expect(moved[0]).toMatchObject({
      cardId: 'c3',
      from: { playerId: 'p1', zone: 'in_play' },
      to: { playerId: 'p1', zone: 'break' },
    });
  });

  it('detects a card broken directly from hand', () => {
    const card = makeCard({ id: 'c4', name: 'Pop', owner: 'p1' });
    const prev = baseState();
    prev.players.p1.hand = [card];
    prev.players.p1.hand_count = 1;

    const next = baseState();
    next.players.p1.hand = [];
    next.players.p1.hand_count = 0;
    next.players.p1.break_zone = [{ ...card, zone: 'Break', is_broken: true }];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'card_moved',
      cardId: 'c4',
      cardName: 'Pop',
      from: { playerId: 'p1', zone: 'hand' },
      to: { playerId: 'p1', zone: 'break' },
    });
  });

  it('detects a fix (break -> hand)', () => {
    const card = makeCard({ id: 'c5', name: 'Fixie', owner: 'p1', zone: 'Break', is_broken: true });
    const prev = baseState();
    prev.players.p1.break_zone = [card];

    const next = baseState();
    next.players.p1.break_zone = [];
    next.players.p1.hand = [{ ...card, zone: 'Hand', is_broken: false }];
    next.players.p1.hand_count = 1;

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'card_moved',
      cardId: 'c5',
      cardName: 'Fixie',
      from: { playerId: 'p1', zone: 'break' },
      to: { playerId: 'p1', zone: 'hand' },
    });
  });

  it('detects a Twist control change without a spurious card_moved', () => {
    const card = makeCard({ id: 'c6', name: 'Twisted', owner: 'p2', controller: 'p2' });
    const prev = baseState();
    prev.players.p2.in_play = [card];

    const next = baseState();
    next.players.p2.in_play = [];
    next.players.p1.in_play = [{ ...card, controller: 'p1' }];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'control_changed',
      cardId: 'c6',
      cardName: 'Twisted',
      fromPlayerId: 'p2',
      toPlayerId: 'p1',
    });
    expect(events.some((e) => e.type === 'card_moved')).toBe(false);
  });

  it('detects a stolen card broken (thief in_play -> owner break) as one card_moved', () => {
    const card = makeCard({ id: 'c7', name: 'Stolen', owner: 'p2', controller: 'p1' });
    const prev = baseState();
    prev.players.p1.in_play = [card];

    const next = baseState();
    next.players.p1.in_play = [];
    next.players.p2.break_zone = [{ ...card, zone: 'Break', is_broken: true, controller: 'p2' }];

    const events = diffGameStates(prev, next);
    const moved = events.filter((e) => e.type === 'card_moved');
    expect(moved).toHaveLength(1);
    expect(moved[0]).toMatchObject({
      cardId: 'c7',
      from: { playerId: 'p1', zone: 'in_play' },
      to: { playerId: 'p2', zone: 'break' },
    });
    expect(events.some((e) => e.type === 'control_changed')).toBe(false);
  });

  it('handles Toynado: multiple moves including a return to a hidden hand', () => {
    const cardA = makeCard({ id: 'c8', name: 'Whirl A', owner: 'p1' });
    const cardB = makeCard({ id: 'c9', name: 'Whirl B', owner: 'p2' });

    const prev = baseState();
    prev.players.p1.in_play = [cardA];
    prev.players.p2.in_play = [cardB];
    prev.players.p2.hand = null;
    prev.players.p2.hand_count = 1;

    const next = baseState();
    next.players.p1.in_play = [];
    next.players.p1.hand = [{ ...cardA, zone: 'Hand' }];
    next.players.p1.hand_count = 1;
    next.players.p2.in_play = [];
    next.players.p2.hand = null;
    next.players.p2.hand_count = 2; // cardB returned to hidden hand

    const events = diffGameStates(prev, next);
    const moved = events.filter((e) => e.type === 'card_moved');
    expect(moved).toContainEqual({
      type: 'card_moved',
      cardId: 'c8',
      cardName: 'Whirl A',
      from: { playerId: 'p1', zone: 'in_play' },
      to: { playerId: 'p1', zone: 'hand' },
    });
    expect(moved).toContainEqual({
      type: 'card_moved',
      cardId: 'c9',
      cardName: 'Whirl B',
      from: { playerId: 'p2', zone: 'in_play' },
      to: { playerId: 'p2', zone: 'hand' },
    });
    expect(moved).toHaveLength(2);
    expect(events.some((e) => e.type === 'hand_count_changed')).toBe(true);
  });

  it('detects damage (current_stamina change)', () => {
    const card = makeCard({ id: 'c10', name: 'Bruised', owner: 'p1', current_stamina: 3 });
    const prev = baseState();
    prev.players.p1.in_play = [card];

    const next = baseState();
    next.players.p1.in_play = [{ ...card, current_stamina: 1 }];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'stat_changed',
      cardId: 'c10',
      cardName: 'Bruised',
      stat: 'current_stamina',
      from: 3,
      to: 1,
    });
  });

  it('detects a buff (strength change)', () => {
    const card = makeCard({ id: 'c11', name: 'Buffed', owner: 'p1', strength: 2 });
    const prev = baseState();
    prev.players.p1.in_play = [card];

    const next = baseState();
    next.players.p1.in_play = [{ ...card, strength: 4 }];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'stat_changed',
      cardId: 'c11',
      cardName: 'Buffed',
      stat: 'strength',
      from: 2,
      to: 4,
    });
  });

  it('detects effective_cost null -> number as a change', () => {
    const card = makeCard({ id: 'c12', name: 'Cheapened', owner: 'p1', effective_cost: null });
    const prev = baseState();
    prev.players.p1.in_play = [card];

    const next = baseState();
    next.players.p1.in_play = [{ ...card, effective_cost: 2 }];

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({
      type: 'stat_changed',
      cardId: 'c12',
      cardName: 'Cheapened',
      stat: 'effective_cost',
      from: null,
      to: 2,
    });
  });

  it('detects charge changes', () => {
    const prev = baseState();
    const next = baseState();
    next.players.p1.charge = 8;

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({ type: 'charge_changed', playerId: 'p1', from: 5, to: 8 });
  });

  it('detects hand_count changes', () => {
    const prev = baseState();
    const next = baseState();
    next.players.p2.hand_count = 5;

    const events = diffGameStates(prev, next);
    expect(events).toContainEqual({ type: 'hand_count_changed', playerId: 'p2', from: 2, to: 5 });
  });

  it('detects turn changes', () => {
    const prev = baseState();
    const next = baseState();
    next.turn_number = 2;
    next.active_player_id = 'p2';

    const events = diffGameStates(prev, next);
    expect(events[0]).toEqual({
      type: 'turn_changed',
      fromTurn: 1,
      toTurn: 2,
      activePlayerId: 'p2',
    });
  });

  it('detects game_over', () => {
    const prev = baseState();
    const next = baseState();
    next.is_game_over = true;
    next.winner = 'p1';

    const events = diffGameStates(prev, next);
    expect(events[events.length - 1]).toEqual({ type: 'game_over', winnerId: 'p1' });
  });

  it('emits nothing for own hidden hand toggling with no other info', () => {
    // Simulate a snapshot where our own hand becomes hidden with the same
    // count and no cards moved elsewhere — no event should be fabricated
    // beyond what's genuinely observable (none here).
    const prev = baseState();
    prev.players.p1.hand = [];
    prev.players.p1.hand_count = 0;

    const next = baseState();
    next.players.p1.hand = null;
    next.players.p1.hand_count = 0;

    const events = diffGameStates(prev, next);
    expect(events).toEqual([]);
  });

  it('emits no card_moved when a hidden hand becomes visible with cards in place', () => {
    const cardA = makeCard({ id: 'c30', name: 'Held A', owner: 'p2', zone: 'Hand' });
    const cardB = makeCard({ id: 'c31', name: 'Held B', owner: 'p2', zone: 'Hand' });

    const prev = baseState();
    prev.players.p2.hand = null;
    prev.players.p2.hand_count = 2;

    const next = baseState();
    next.players.p2.hand = [cardA, cardB];
    next.players.p2.hand_count = 2;

    const events = diffGameStates(prev, next);
    expect(events.filter((e) => e.type === 'card_moved')).toEqual([]);
  });

  it('emits no card_moved when a visible hand becomes hidden with cards in place', () => {
    const cardA = makeCard({ id: 'c32', name: 'Held C', owner: 'p2', zone: 'Hand' });

    const prev = baseState();
    prev.players.p2.hand = [cardA];
    prev.players.p2.hand_count = 1;

    const next = baseState();
    next.players.p2.hand = null;
    next.players.p2.hand_count = 1;

    const events = diffGameStates(prev, next);
    expect(events.filter((e) => e.type === 'card_moved')).toEqual([]);
  });

  it('produces a fully ordered event list for a combined multi-event turn', () => {
    const played = makeCard({ id: 'c20', name: 'Played', owner: 'p1' });
    const broken = makeCard({ id: 'c21', name: 'Broken', owner: 'p2' });
    const buffed = makeCard({ id: 'c22', name: 'Buffed', owner: 'p1', strength: 1 });

    const prev = baseState();
    prev.turn_number = 3;
    prev.active_player_id = 'p1';
    prev.players.p1.hand = [played];
    prev.players.p1.hand_count = 1;
    prev.players.p1.in_play = [buffed];
    prev.players.p2.in_play = [broken];
    prev.players.p1.charge = 4;

    const next = baseState();
    next.turn_number = 4;
    next.active_player_id = 'p2';
    next.players.p1.hand = [];
    next.players.p1.hand_count = 0;
    next.players.p1.in_play = [{ ...played, zone: 'InPlay' }, { ...buffed, strength: 3 }];
    next.players.p2.in_play = [];
    next.players.p2.break_zone = [{ ...broken, zone: 'Break', is_broken: true }];
    next.players.p1.charge = 6;

    const events = diffGameStates(prev, next);

    expect(events[0]).toEqual({
      type: 'turn_changed',
      fromTurn: 3,
      toTurn: 4,
      activePlayerId: 'p2',
    });

    const chargeIdx = events.findIndex((e) => e.type === 'charge_changed');
    const handCountIdx = events.findIndex((e) => e.type === 'hand_count_changed');
    const movedIdxs = events
      .map((e, i) => (e.type === 'card_moved' ? i : -1))
      .filter((i) => i >= 0);
    const statIdx = events.findIndex((e) => e.type === 'stat_changed');

    expect(chargeIdx).toBeGreaterThan(0);
    expect(handCountIdx).toBeGreaterThan(chargeIdx);
    expect(Math.min(...movedIdxs)).toBeGreaterThan(handCountIdx);
    expect(statIdx).toBeGreaterThan(Math.max(...movedIdxs));

    expect(events).toContainEqual({
      type: 'charge_changed',
      playerId: 'p1',
      from: 4,
      to: 6,
    });
    expect(events).toContainEqual({
      type: 'hand_count_changed',
      playerId: 'p1',
      from: 1,
      to: 0,
    });
    expect(events).toContainEqual({
      type: 'card_moved',
      cardId: 'c20',
      cardName: 'Played',
      from: { playerId: 'p1', zone: 'hand' },
      to: { playerId: 'p1', zone: 'in_play' },
    });
    expect(events).toContainEqual({
      type: 'card_moved',
      cardId: 'c21',
      cardName: 'Broken',
      from: { playerId: 'p2', zone: 'in_play' },
      to: { playerId: 'p2', zone: 'break' },
    });
    expect(events).toContainEqual({
      type: 'stat_changed',
      cardId: 'c22',
      cardName: 'Buffed',
      stat: 'strength',
      from: 1,
      to: 3,
    });
  });

  it('never throws on well-formed but sparse states', () => {
    const prev = makeState({ players: {} });
    const next = makeState({ players: {} });
    expect(() => diffGameStates(prev, next)).not.toThrow();
    expect(diffGameStates(prev, next)).toEqual([]);
  });
});

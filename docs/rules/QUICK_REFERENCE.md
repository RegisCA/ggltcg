# GGLTCG Quick Reference

*Authoritative source: `docs/rules/GGLTCG Rules v1_1.md`*

## Game Overview

- **Players**: 2
- **Cards per player**: 6 unique cards (no duplicates)
- **Win condition**: Put all opponent's cards into their Sleep Zone

## Zones (3 per player)

| Zone | Description |
|------|-------------|
| **Hand** | Cards you hold before playing. Hidden from opponent. |
| **In Play** | Where Toys go after being played. Cards here are "awake" and active. |
| **Sleep Zone** | Where sleeped cards go. Face-up, visible to both players. |

## CC (Charge Counters)

| Rule | Detail |
|------|--------|
| **Turn 1 (first turn of game)** | Active player gains 2 CC |
| **Turn 2+ (all subsequent turns)** | Active player gains 4 CC at start of turn |
| **Carry over** | Unspent CC saved for your next turn |
| **Maximum** | 7 CC per player (excess is lost) |

**Turn sequence**: Turns alternate between players.
- Turn 1: Player 1 (gains 2 CC)
- Turn 2: Player 2 (gains 4 CC)
- Turn 3: Player 1 (gains 4 CC + any carried over)
- Turn 4: Player 2 (gains 4 CC + any carried over)
- etc.

## Card Types

| Type | Behavior |
|------|----------|
| **Toy** | Has Speed/Strength/Stamina stats. Stays In Play until sleeped. Can tussle. |
| **Action** | No stats. Effect resolves immediately, then card goes to your Sleep Zone. |

## Actions & Costs

| Action | Cost | Notes |
|--------|------|-------|
| **Play a card** | Card's printed cost | Pay CC, card enters In Play (Toy) or resolves (Action) |
| **Tussle** | 2 CC (default) | Your Toy vs opponent's Toy. Can be modified by card effects. |
| **Direct Attack** | 2 CC (default) | Only when opponent has no Toys In Play. Max 2 per turn. Random card from opponent's Hand → Sleep Zone. |
| **Activate** | 1 CC | Trigger an activated ability (e.g., Archer) |

## Tussle Resolution

1. Compare Speed (active player's Toy gets +1 Speed bonus)
2. Higher Speed strikes first
3. Strike deals Strength as damage to opponent's Stamina
4. Stamina ≤ 0 → card is sleeped
5. If speeds tied, both strike simultaneously

**Key rule**: Toys can tussle the same turn they are played.

## Zone Changes

When a card moves between zones, all modifications reset (stat changes, damage, temporary effects). Card enters new zone with original printed values.

## Card Data

Current cards and effects: `backend/data/cards.csv`

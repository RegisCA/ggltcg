# Effect System

Every card ability in GGLTCG is defined as data. A card's row in
`backend/data/cards.csv` carries a short effect string, the engine parses it into
effect objects, and those objects hook into the rules at fixed points: stat
calculation, cost calculation, playing a card, breaking a card, the start of a
turn. No card has its own class. Copy, Twist and Knight, which once looked too
unusual for a generic system, are parameterised effects like the rest.

This document explains the DSL, the class families, where each family plugs
into the engine, how targeting works and how transformed cards survive a save.
For the step-by-step guide to adding a card, and the syntax of every effect
type, see [ADDING_NEW_CARDS.md](ADDING_NEW_CARDS.md).

- [From CSV to behaviour](#from-csv-to-behaviour)
- [The effect DSL](#the-effect-dsl)
- [Effect families](#effect-families)
- [Where effects hook into the engine](#where-effects-hook-into-the-engine)
- [Targeting](#targeting)
- [Copy and transformation](#copy-and-transformation)
- [Testing and debugging](#testing-and-debugging)
- [Design notes](#design-notes)

## From CSV to behaviour

```text
cards.csv                     "stat_boost:strength:2"       the source of truth
   │  CardLoader
   ▼
Card.effect_definitions       same string, copied onto each card instance;
   │                          serialised with the game, never the objects
   │  EffectRegistry.get_effects(card)
   ▼
EffectFactory.parse_effects   splits on ";", dispatches on the keyword,
   │                          validates parameters
   ▼
[StatBoostEffect(Ka, strength, +2)]
   │
   ▼
GameEngine                    get_card_stat, calculate_card_cost, play_card,
                              _break_card, start_turn, ...
```

The string is the only persistent form of an effect. Effect objects are built on
demand and thrown away, so they hold no state of their own: anything that has to
persist (damage, a turn-long stat boost, a transformation) lives on the `Card`.

## The effect DSL

A card's `effects` column holds zero or more effect definitions separated by
`;`. Each definition is a keyword followed by `:`-separated parameters.

| Card | `effects` | Meaning |
| --- | --- | --- |
| Ka | `stat_boost:strength:2` | Your cards have +2 strength |
| Archer | `cannot_tussle;remove_stamina_ability:1` | Two effects: can't tussle; can pay Charge to remove stamina |
| Raggy | `set_self_tussle_cost:0:not_turn_1` | Its tussles are free, except on turn 1 |
| Rush | `gain_charge:2:not_first_turn` | Gain 2 Charge; not playable on your first turn |
| Dream | `reduce_cost_by_broken` | Costs 1 less per card in your break zone |
| That was fun | `fix:actions:1` | Return one Action from your break zone to your hand |
| Sock Serpent | `break_target:1:opponent` | When played, you may break an opponent's card |
| Copy | `copy_card` | Becomes a copy of one of your cards in play |
| Car | *(empty)* | No ability, just stats |

Parsing rules (`EffectFactory.parse_effects`, `rules/effects/effect_registry.py`):

- The keyword is case-insensitive; empty definitions are ignored.
- Each keyword has its own small parser that checks the parameter count and
  types, and raises `ValueError` on anything unexpected. An unknown keyword
  also raises.
- Trailing modifiers are specific to one keyword: `not_first_turn` on
  `gain_charge` (the player's own first turn), `not_turn_1` on
  `set_self_tussle_cost` (game turn 1), a target scope `any|opponent` on
  `break_target` and `return_target_to_hand`, and a card-type filter on `fix`.
- There is no trigger prefix. When an effect fires is determined by its
  family: a play effect on an Action fires when the Action is played, the same
  play effect on a Toy is that Toy's "when played" ability, and triggered
  effects carry their timing in the keyword (`gain_charge_when_broken`,
  `start_of_turn_gain_charge`).

The same keyword works on either card type. Candy Golem (`gain_charge:4`) is a
Toy using the effect that Cake, an Action, also uses; the engine resolves it
when the Toy enters play.

## Effect families

All effect classes derive from `BaseEffect` (`rules/effects/base_effect.py`).
There are 27 keywords, each mapped to one class:

| Family | Base class | Interface | Keywords |
| --- | --- | --- | --- |
| Continuous: stats | `ContinuousEffect` | `modify_stat(card, stat, value, state)` | `stat_boost` |
| Continuous: costs | `CostModificationEffect` | `modify_card_cost(...)`, `modify_tussle_cost(...)` | `set_tussle_cost`, `set_self_tussle_cost`, `reduce_cost_by_broken`, `self_cost_increase_by_broken`, `opponent_cost_increase`, `alternative_cost_break_card` |
| Continuous: protection | `ProtectionEffect` | `is_protected_from(effect, state)` | `opponent_immunity`, `team_opponent_immunity` |
| Continuous: rule changes | `ContinuousEffect` | duck-typed checks such as `can_tussle`, `wins_tussle` | `cannot_tussle`, `direct_attack`, `auto_win_tussle_on_own_turn` |
| Triggered | `TriggeredEffect` | `trigger`, `should_trigger`, `apply` | `gain_charge_when_broken`, `start_of_turn_gain_charge`, `on_card_played_gain_charge`, `damage_all_opponent_cards` |
| Play | `PlayEffect` | `apply`, plus the targeting methods below | `gain_charge`, `fix`, `break_all`, `break_target`, `return_target_to_hand`, `return_all_to_hand`, `take_control`, `copy_card`, `turn_stat_boost`, `opponent_lose_all_charge` |
| Activated | `ActivatedEffect` | `cost_charge`, `can_apply`, `apply` | `remove_stamina_ability` |

Classes live in `continuous_effects.py` and `action_effects.py`. The dispatch
from keyword to class is a single function, `EffectFactory.parse_effects`, so
it is the one place to look when tracing a card's behaviour.

## Where effects hook into the engine

Every consumer asks `EffectRegistry.get_effects(card)` for a card's effects and
filters by type. Nothing subscribes or registers; the engine asks at the moment
it needs an answer.

| Hook | Engine method | What it asks |
| --- | --- | --- |
| Stats | `GameEngine.get_card_stat` | Every continuous effect in play may modify any card's stat |
| Card cost | `GameEngine.calculate_card_cost` | Variable cost from the target (Copy, Glue, Stomp), then every cost modifier in play and the card's own |
| Tussle cost | `GameEngine.calculate_tussle_cost` | The cheapest applicable `set_tussle_cost` / `set_self_tussle_cost` (default 2) |
| Can it play / tussle? | `can_play_card`, `can_tussle` | `PlayEffect.can_apply` (Rush), `can_tussle` (Archer, Raggy), `direct_attack` (Paper Plane) |
| Playing an Action | `_resolve_action_card` | Apply every play effect, then move the card to the break zone |
| Playing a Toy | `_trigger_when_played_effects` | After it enters play, apply its play effects and `WHEN_PLAYED` triggers |
| Another card played | `_trigger_when_other_card_played_effects` | Hind Leg Kicker's Charge gain |
| Start of turn | `_trigger_start_of_turn_effects` | Belchaletta's Charge gain |
| Breaking | `_break_card` | `WHEN_BROKEN` triggers (Umbruh), only if the card was in play |
| Tussle resolution | `_execute_tussle` | Knight's `wins_tussle` on its controller's turn |
| Protection | `GameState.is_protected_from_effect` | The card's own protection, then any team-wide protection in play |

Because stats and costs are always recomputed from what is in play, an effect
stops applying the moment its source leaves play. There is nothing to undo.

Protection is checked by the effects that would touch a card: targeting
filters, board-wide effects such as Clean and Toynado, Gibbers' cost increase
and Knight's automatic win all skip a protected card.

## Targeting

A play effect that needs targets overrides four methods:

```python
requires_targets() -> bool
get_valid_targets(game_state, player) -> list[Card]
get_min_targets() -> int
get_max_targets() -> int
```

`ActionValidator` turns these into a `ValidAction` with `target_options` (card
IDs), `min_targets` and `max_targets`. The web client shows those options in
its target picker, and the AI's enumerator branches over them. Neither has any
targeting logic of its own.

When the action comes back, `ActionExecutor` resolves the IDs to cards and
rejects any ID outside the effect's current `get_valid_targets`, so a stale or
forged request cannot target an illegal card. The target is resolved before the
cost is computed, because a variable-cost card's price depends on what it
targets.

**Optional targets.** A Toy's "when played" targeting is always optional: the
printed text says "you may", and a Toy can always be played for its body alone.
`PlayEffect.get_min_targets` returns 0 when the source is a Toy, and the
validator still offers a Toy whose effect has no legal target. An Action's
targeting is required by default (Drop needs something to break), and an
Action with no legal target is not offered. `fix` is optional on both types.

## Copy and transformation

Copy and Clone (`copy_card`) turn into a full copy of one of your cards in
play. `CopyEffect.apply`:

1. Marks the card `_is_transformed` and renames it "Copy of Ka".
2. Copies the target's type, cost, stats, colours and `effect_definitions`.
3. Pre-parses the borrowed effects into `_copied_effects`.

`EffectRegistry.get_effects` returns `_copied_effects` when present, so from
then on the copy behaves exactly like the original. Because the borrowed effect
string is stored on the card, a saved game rebuilds `_copied_effects` on load
(`api/serialization.py`). When the copy leaves play, `Card.reset_modifications`
restores the original Copy card.

A copy of a Toy with a "when played" ability does not trigger it: the copy was
not played from hand. The same applies to a Toy taken with Twist.

## Testing and debugging

- **Card data integrity** (`tests/test_card_data_integrity.py`) runs in CI and
  checks every row of `cards.csv`: unique names, valid costs and colours,
  all-or-nothing stats, every effect string parses, and every card with an
  effect has AI guidance in `card_guidance.yaml`.
- **Per-card behaviour**: one test module per card batch
  (`test_batch1_vanilla_toys.py` to `test_batch4_when_played_cards.py`), plus
  modules for individual cards and past bugs (`test_gibbers.py`,
  `test_paper_plane.py`, `test_copy_transformation_reset.py`, ...).
  `conftest.create_game_with_cards` builds a game with chosen cards in chosen
  zones.
- **Serialization** (`tests/test_comprehensive_serialization.py`) round-trips
  every zone, multi-effect cards and transformed Copies through save and load,
  then checks that stats still compute correctly.
- **`GET /games/{id}/debug`** returns every card's effect string, its parsed
  effect classes, any copied effects, and base versus effective stats. It is a
  development tool and exposes both hands.

## Design notes

**Why a DSL rather than one class per card.** The original implementation had a
Python class per card and a name-based registry. Every new card meant new code,
and two cards with the same ability had two implementations. Generic,
parameterised effects mean the 45 current cards share 27 effect types, most new
cards need only a CSV row, and the game's designer can read the definitions.

**Why rebuild effects on demand.** Building effect objects from the stored
string every time keeps them stateless and makes serialisation trivial: save the
string, never the object. The cost is repeated parsing inside hot paths such as
stat calculation. At the current scale this is not measurable in play, but it
is the obvious first optimisation if the AI's search ever needs to go deeper.

**Known gaps.**

- Activated abilities (Archer) are applied in the action route rather than
  through `ActionExecutor`, so their target check is weaker than for card
  plays.
- `remove_stamina_ability` parses its cost parameter but the ability always
  costs 1 Charge per activation.
- `damage_all_opponent_cards` (Monster) affects every other card on both sides,
  as its card text says; the keyword name predates that.

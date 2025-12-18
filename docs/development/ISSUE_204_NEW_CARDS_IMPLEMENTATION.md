# Issue #204: New Cards Implementation Plan

**Date:** December 6, 2025 **Status:** Planning Complete **Branch:**
`feature/issue-204-new-cards`

## Overview

This document provides a detailed analysis and implementation plan for adding 9
new cards to GGLTCG as specified in Issue #204. The cards have been added to
`backend/data/cards_beta_20251206.csv` with preliminary effect definitions.

---

## Card Analysis Summary

- **Surge** (Action, Cost 0)
- Effect: Gain 1 CC
- Complexity: 🟢 Trivial
- Priority: 1

- **Dwumm** (Toy, Cost 1)
- Effect: Your cards have +2 speed
- Complexity: 🟢 Very Easy
- Priority: 2

- **Twombon** (Toy, Cost 1)
- Effect: Your cards have +2 strength
- Complexity: 🟢 Very Easy
- Priority: 3

- **Drop** (Action, Cost 1)
- Effect: Sleep a card in play (targeted)
- Complexity: 🟡 Easy
- Priority: 4

- **Jumpscare** (Action, Cost 0)
- Effect: Return a card in play to owner's hand (targeted)
- Complexity: 🟡 Easy
- Priority: 5

- **Sock Sorcerer** (Toy, Cost 3)
- Effect: Your cards are immune to opponent effects
- Complexity: 🟡 Medium
- Priority: 6

- **VeryVeryAppleJuice** (Action, Cost 0)
- Effect: This turn, +1 all stats
- Complexity: 🟠 Medium-Hard
- Priority: 7

- **Belchaletta** (Toy, Cost 1)
- Effect: Start of turn: gain 2 CC
- Complexity: 🟠 Hard
- Priority: 8

- **Hind Leg Kicker** (Toy, Cost 1)
- Effect: When you play another card, gain 1 CC
- Complexity: 🔴 Hardest
- Priority: 9
CC — Complexity: 🔴 Hardest — Priority: 9

---

## Detailed Card Analysis

### 1. Surge (🟢 TRIVIAL - Already Working!)

**Effect:** "Gain 1 CC."

**Effect Definition:** `gain_cc:1`

**Implementation Status:** ✅ **COMPLETE** - You confirmed this works in testing!

**How It Works:**

- Uses existing `GainCCEffect` class in `action_effects.py`
- Parser already exists: `_parse_gain_cc()` in `effect_registry.py`
- No restrictions (unlike Rush's `not_first_turn`)

**Testing:** Add basic test to confirm parsing and application.

**AI Awareness:**

```python
"Surge": {
    "type": "Action",
    "effect": "Gain 1 CC",
    "strategic_use": "FREE CC - Use when you need 1 more CC for a key play. Lower value than Rush but playable on turn 1.",
    "threat_level": "LOW - Small CC advantage for opponent"
}

```

---

### 2. Dwumm (🟢 VERY EASY)

**Effect:** "Your cards have 2 more speed." **Effect Definition:**
`stat_boost:speed:2`

**Implementation Status:** ✅ **COMPLETE** - Uses existing patterns!

**How It Works:**
- Uses existing `StatBoostEffect` class in `continuous_effects.py`
- Parser exists: `_parse_stat_boost()` - supports `speed`, `strength`,
`stamina`, or `all`

- Same pattern as Ka (`stat_boost:strength:2`)

**Testing:** Similar to `test_ka_effect()` in `test_data_driven_effects.py`

**AI Awareness:**

```python
"Dwumm": {
    "type": "Toy",
    "effect": "Continuous: All your Toys get +2 Speed",
    "strategic_use": "SPEED ADVANTAGE - Makes your cards strike first in tussles. Great with strong attackers.",
    "threat_level": "HIGH - Opponent's cards will strike first against yours"
}

```

---

### 3. Twombon (🟢 VERY EASY)

**Effect:** "Your cards have 2 more strength." **Effect Definition:**
`stat_boost:strength:2`

**Implementation Status:** ✅ **COMPLETE** - Identical to Ka!

**How It Works:**
- Uses existing `StatBoostEffect` class
- Same effect definition as Ka
- Ka is 2 cost, Twombon is 1 cost (but weaker stats: 2/2/2 vs 5/9/1)

**Testing:** Can share tests with Ka

**AI Awareness:**

```python
"Twombon": {
    "type": "Toy",
    "effect": "Continuous: All your Toys get +2 Strength",
    "strategic_use": "FORCE MULTIPLIER - Like Ka but cheaper. Lower stats make it more vulnerable.",
    "threat_level": "HIGH - Boosts opponent's entire board"
}

```

---

### 4. Drop (🟡 EASY - New Effect Type)

**Effect:** "Sleep a card that is in play." **Effect Definition:** Needs new
type: `sleep_target:1` (1 target from all in play)

**Implementation Needed:**

1. **New Effect Class:** `SleepTargetEffect` in `action_effects.py`

   ```python
   class SleepTargetEffect(PlayEffect):
       """Sleep a targeted card in play."""

       def __init__(self, source_card: "Card", count: int = 1):
           super().__init__(source_card)
           self.count = count

       def requires_targets(self) -> bool:
           return True

       def get_valid_targets(self, game_state, player=None) -> List[Card]:
           """All cards in play from both players (except protected ones)."""
           all_cards = game_state.get_all_cards_in_play()
           return [c for c in all_cards if not game_state.is_protected_from_effect(c, self)]

       def apply(self, game_state, **kwargs):
           targets = kwargs.get("targets", [])
           game_engine = kwargs.get("game_engine")
           for target in targets[:self.count]:
               if game_engine:
                   owner = game_state.get_card_owner(target)
                   game_engine._sleep_card(target, owner, was_in_play=True)
               else:
                   game_state.sleep_card(target, was_in_play=True)

   ```

1. **New Parser:** `_parse_sleep_target()` in `effect_registry.py`

1. **CSV Update:** `sleep_target:1`

**AI Awareness:**

```python
"Drop": {
    "type": "Action",
    "effect": "Target: Sleep any card in play (yours or opponent's)",
    "strategic_use": "PRECISION REMOVAL - Sleep a specific threat. Cheaper than Clean but only one target.",
    "threat_level": "HIGH - Can sleep your best card"
}

```text

---

### 5. Jumpscare (🟡 EASY - New Effect Type)

**Effect:** "Put a card that is in play into their owner's hand." **Effect
Definition:** Needs new type: `return_target_to_hand:1`

**Implementation Needed:**

1. **New Effect Class:** `ReturnTargetToHandEffect` in `action_effects.py`

   ```python
   class ReturnTargetToHandEffect(PlayEffect):
       """Return a targeted card to its owner's hand."""

       def __init__(self, source_card: "Card", count: int = 1):
           super().__init__(source_card)
           self.count = count

       def requires_targets(self) -> bool:
           return True

       def get_valid_targets(self, game_state, player=None) -> List[Card]:
           """All cards in play from both players (except protected)."""
           all_cards = game_state.get_all_cards_in_play()
           return [c for c in all_cards if not game_state.is_protected_from_effect(c, self)]

       def apply(self, game_state, **kwargs):
           targets = kwargs.get("targets", [])
           for target in targets[:self.count]:
               if game_state.is_protected_from_effect(target, self):
                   continue
               owner = game_state.get_card_owner(target)
               # Remove from play
               for p in game_state.players.values():
                   if target in p.in_play:
                       p.in_play.remove(target)
                       break
               # Return to owner's hand
               game_state.return_card_to_hand(target, owner)

   ```

1. **New Parser:** `_parse_return_target_to_hand()` in `effect_registry.py`

1. **CSV Update:** `return_target_to_hand:1`

**AI Awareness:**

```python
"Jumpscare": {
    "type": "Action",
    "effect": "Target: Return any card in play to owner's hand (no sleep trigger)",
    "strategic_use": "TEMPO REMOVAL - Bounce a threat without triggering when-sleeped. Great vs Umbruh!",
    "threat_level": "MEDIUM - Can bounce your key card back to hand"
}

```text

---

### 6. Sock Sorcerer (🟡 MEDIUM - Extend Existing Pattern)

**Effect:** "Your opponent's cards' effects don't affect your cards." **Effect
Definition:** Needs new pattern: `team_opponent_immunity` (like Beary but for
all your cards)

**Implementation Needed:**

1. **New Effect Class:** `TeamOpponentImmunityEffect` in `continuous_effects.py`

   ```python
   class TeamOpponentImmunityEffect(ProtectionEffect):
       """
       All cards controlled by this card's controller are immune
       to effects from opponent-controlled cards.
       """

       def protects_card(self, target_card: Card, effect_source: Card,
                        game_state: GameState) -> bool:
           # Only protects if Sock Sorcerer is in play
           if self.source_card.zone != Zone.IN_PLAY:
               return False

           # Get controllers
           sorcerer_controller = game_state.get_card_controller(self.source_card)
           target_controller = game_state.get_card_controller(target_card)
           effect_source_controller = game_state.get_card_controller(effect_source)

           # Protect all cards controlled by Sock Sorcerer's controller
           # from effects controlled by opponents
           if target_controller == sorcerer_controller:
               if effect_source_controller != sorcerer_controller:
                   return True
           return False

   ```

1. **Modify `is_protected_from_effect()`** in `game_state.py` to check all
protection effects

1. **New Parser:** `_parse_team_opponent_immunity()` in `effect_registry.py`

1. **CSV Update:** `team_opponent_immunity`

**AI Awareness:**

```python
"Sock Sorcerer": {
    "type": "Toy",
    "effect": "Continuous: All your Toys are immune to opponent's card effects (like team-wide Beary)",
    "strategic_use": "TEAM PROTECTION - Protects all your cards from Twist, Clean, Copy, etc. Very powerful!",
    "threat_level": "CRITICAL - Your Action cards won't affect opponent's board"
}

```text

---

### 7. VeryVeryAppleJuice (🟠 MEDIUM-HARD - Turn-Scoped Effect)

**Effect:** "This turn, your cards have 1 more of each stat." **Effect
Definition:** Needs new pattern: `turn_stat_boost:all:1`

**Challenge:** Effect must expire at end of turn (unlike Ka/Demideca which are
permanent while in play).

**Implementation Approach:**

**Option A: Turn-Scoped Modification (Simpler)**
1. Add turn marker to player's modifications
1. Effect applies modification with turn number
1. Stat calculation ignores modifications from previous turns

**Option B: End-of-Turn Cleanup (More Complex)**
1. Apply modifications to all cards
1. Register cleanup callback for end of turn
1. Clean up modifications when turn ends

**Recommended: Option A**

1. **New Effect Class:** `TurnStatBoostEffect` in `action_effects.py`

   ```python
   class TurnStatBoostEffect(PlayEffect):
       """
       Boost all player's card stats for the current turn only.
       Uses turn_modifications which are cleared at turn end.
       """

       def __init__(self, source_card: Card, stat_name: str, amount: int):
           super().__init__(source_card)
           self.stat_name = stat_name  # "all", "speed", etc.
           self.amount = amount

       def apply(self, game_state, **kwargs):
           player = kwargs.get("player")
           turn = game_state.turn_number

           # Apply turn-scoped boost to all player's toys in play
           for card in player.in_play:
               if card.is_toy():
                   if not hasattr(card, 'turn_modifications'):
                       card.turn_modifications = {}

                   key = f"turn_{turn}_boost"
                   card.turn_modifications[key] = {
                       "turn": turn,
                       "stat": self.stat_name,
                       "amount": self.amount
                   }

   ```

1. **Modify `get_card_stat()`** to include turn-scoped modifications

1. **Clear expired modifications** at start of turn or during stat calculation

**AI Awareness:**

```python
"VeryVeryAppleJuice": {
    "type": "Action",
    "effect": "This turn: All your Toys get +1 Speed, +1 Strength, +1 Stamina",
    "strategic_use": "COMBAT BUFF - Use before tussling to win fights you'd otherwise lose. One turn only!",
    "threat_level": "MEDIUM - Temporary boost makes opponent's tussles stronger this turn"
}

```text

---

### 8. Belchaletta (🟠 HARD - Start-of-Turn Trigger)

**Effect:** "At the start of your turn, gain 2 charge." **Effect Definition:**
Needs new pattern: `start_of_turn_gain_cc:2`

**Challenge:** Requires triggering effects at start of turn - mechanism
partially exists in `TriggerTiming.START_OF_TURN` but isn't wired up.

**Implementation Needed:**

1. **New Effect Class:** `StartOfTurnGainCCEffect` in `continuous_effects.py`

   ```python
   class StartOfTurnGainCCEffect(TriggeredEffect):
       """Gain CC at the start of controller's turn."""

       def __init__(self, source_card: Card, amount: int):
           super().__init__(source_card, TriggerTiming.START_OF_TURN, is_optional=False)
           self.amount = amount

       def should_trigger(self, game_state, **kwargs) -> bool:
           # Only trigger if card is in play
           if self.source_card.zone != Zone.IN_PLAY:
               return False
           # Only trigger on controller's turn
           controller = game_state.get_card_controller(self.source_card)
           active_player = game_state.get_active_player()
           return controller == active_player

       def apply(self, game_state, **kwargs):
           controller = game_state.get_card_controller(self.source_card)
           controller.gain_cc(self.amount)

   ```

1. **Modify `start_turn()` in `game_engine.py`:**

   ```python
   def start_turn(self) -> None:
       # ... existing code ...

       # NEW: Trigger start-of-turn effects
       self._trigger_start_of_turn_effects()

       # Move to main phase
       self.game_state.phase = Phase.MAIN

   def _trigger_start_of_turn_effects(self):
       """Trigger all START_OF_TURN effects for active player's cards."""
       player = self.game_state.get_active_player()
       for card in player.in_play:
           effects = EffectRegistry.get_effects(card)
           for effect in effects:
               if isinstance(effect, TriggeredEffect):
                   if effect.trigger == TriggerTiming.START_OF_TURN:
                       if effect.should_trigger(self.game_state):
                           effect.apply(self.game_state, player=player, game_engine=self)

   ```

1. **New Parser:** `_parse_start_of_turn_gain_cc()` in `effect_registry.py`

1. **CSV Update:** `start_of_turn_gain_cc:2`

**AI Awareness:**

```python
"Belchaletta": {
    "type": "Toy",
    "effect": "Triggered: At start of your turn, gain 2 CC",
    "strategic_use": "CC ENGINE - Generates 2 extra CC every turn. Huge value if it survives multiple turns!",
    "threat_level": "HIGH - Opponent gains +2 CC per turn on top of normal 4"
}

```text

---

### 9. Hind Leg Kicker (🔴 HARDEST - On-Play Trigger)

**Effect:** "When you play a card (not this one), gain 1 charge." **Effect
Definition:** Needs new pattern: `on_card_played_gain_cc:1`

**Challenge:** Requires a trigger that fires when OTHER cards are played - new
trigger type needed.

**Implementation Needed:**

1. **New TriggerTiming:** `WHEN_OTHER_CARD_PLAYED`

1. **New Effect Class:** `OnCardPlayedGainCCEffect` in `continuous_effects.py`

   ```python
   class OnCardPlayedGainCCEffect(TriggeredEffect):
       """Gain CC when controller plays another card."""

       def __init__(self, source_card: Card, amount: int):
           super().__init__(source_card, TriggerTiming.WHEN_OTHER_CARD_PLAYED, is_optional=False)
           self.amount = amount

       def should_trigger(self, game_state, **kwargs) -> bool:
           if self.source_card.zone != Zone.IN_PLAY:
               return False

           played_card = kwargs.get("played_card")
           player = kwargs.get("player")

           # Don't trigger for itself
           if played_card == self.source_card:
               return False

           # Only trigger for controller's plays
           controller = game_state.get_card_controller(self.source_card)
           return controller == player

       def apply(self, game_state, **kwargs):
           controller = game_state.get_card_controller(self.source_card)
           controller.gain_cc(self.amount)

   ```

1. **Modify `play_card()` in `game_engine.py`:**

   ```python
   def play_card(self, player, card, **kwargs):
       # ... existing play logic ...

       # After card is successfully played:
       # Trigger "when card played" effects from OTHER cards
       self._trigger_on_card_played_effects(card, player)

   def _trigger_on_card_played_effects(self, played_card: Card, player: Player):
       """Trigger effects that respond to cards being played."""
       for card in player.in_play:
           if card == played_card:
               continue  # Skip the card that was just played
           effects = EffectRegistry.get_effects(card)
           for effect in effects:
               if isinstance(effect, TriggeredEffect):
                   if effect.trigger == TriggerTiming.WHEN_OTHER_CARD_PLAYED:
                       if effect.should_trigger(self.game_state,
                                               played_card=played_card, player=player):
                           effect.apply(self.game_state, player=player, game_engine=self)

   ```

1. **New Parser:** `_parse_on_card_played_gain_cc()` in `effect_registry.py`

1. **CSV Update:** `on_card_played_gain_cc:1`

**AI Awareness:**

```python
"Hind Leg Kicker": {
    "type": "Toy",
    "effect": "Triggered: When you play another card, gain 1 CC",
    "strategic_use": "CC REFUND - Each card you play refunds 1 CC. Great for combo turns with many plays!",
    "threat_level": "MEDIUM - Opponent gets partial CC refund on plays"
}

```text

---

## Implementation Plan

### Phase 1: Trivial/Easy Cards (Batch 1)

**Estimated Time:** 1-2 hours **Cards:** Surge, Dwumm, Twombon

1. ✅ Surge already works - just add test
1. Fix CSV effect definitions (remove `{}` placeholders)
1. Add AI prompt entries
1. Write tests for all three
1. Test manually against AI

### Phase 2: New Targeted Effects (Batch 2)

**Estimated Time:** 2-3 hours **Cards:** Drop, Jumpscare

1. Implement `SleepTargetEffect` class
1. Add `_parse_sleep_target()` parser
1. Implement `ReturnTargetToHandEffect` class
1. Add `_parse_return_target_to_hand()` parser
1. Update CSV with proper effect definitions
1. Add AI prompt entries
1. Write tests
1. Test manually against AI

### Phase 3: Protection Effect Extension (Batch 3)

**Estimated Time:** 2-3 hours **Cards:** Sock Sorcerer

1. Implement `TeamOpponentImmunityEffect` class
1. Update `is_protected_from_effect()` to check team immunity
1. Add `_parse_team_opponent_immunity()` parser
1. Update CSV
1. Add AI prompt entry
1. Write comprehensive tests (interactions with various effects)
1. Test manually against AI

### Phase 4: Turn-Scoped Effects (Batch 4)

**Estimated Time:** 3-4 hours **Cards:** VeryVeryAppleJuice

1. Design turn-scoped modification system
1. Implement `TurnStatBoostEffect` class
1. Modify stat calculation to include turn modifications
1. Add cleanup mechanism for expired modifications
1. Add parser
1. Update CSV
1. Add AI prompt entry
1. Write tests (including turn boundary tests)
1. Test manually against AI

### Phase 5: Triggered Effects (Batch 5)

**Estimated Time:** 4-5 hours **Cards:** Belchaletta, Hind Leg Kicker

1. Add `START_OF_TURN` trigger to game engine
1. Implement `StartOfTurnGainCCEffect` for Belchaletta
1. Add new `WHEN_OTHER_CARD_PLAYED` trigger timing
1. Modify `play_card()` to trigger on-play effects
1. Implement `OnCardPlayedGainCCEffect` for Hind Leg Kicker
1. Add parsers for both
1. Update CSV
1. Add AI prompt entries
1. Write comprehensive tests
10. Test manually against AI

---

## Testing Strategy

### Unit Tests (per card)

Each card should have tests for:

1. **Effect parsing:** CSV definition correctly creates effect object
1. **Effect application:** Effect works as expected
1. **Protection interactions:** Beary/Sock Sorcerer immunity respected
1. **Edge cases:** Empty targets, multiple instances, etc.

### Integration Tests

1. **Turn boundary tests:** Effects that span turns work correctly
1. **Trigger ordering:** Multiple triggered effects fire in correct order
1. **AI decision making:** AI correctly evaluates and uses new cards

### Test File Structure

```text
backend/tests/
├── test_new_cards_phase1.py  # Surge, Dwumm, Twombon
├── test_new_cards_phase2.py  # Drop, Jumpscare
├── test_new_cards_phase3.py  # Sock Sorcerer
├── test_new_cards_phase4.py  # VeryVeryAppleJuice
└── test_new_cards_phase5.py  # Belchaletta, Hind Leg Kicker

```text

---

## AI Player Updates

### Required Changes to `prompts.py`

1. Add all 9 cards to `CARD_EFFECTS_LIBRARY`
1. Update strategic guidance for:
- Speed buffs (Dwumm makes tussle order predictions change)
- Turn-scoped effects (VeryVeryAppleJuice is time-sensitive)
- CC generation cards (Belchaletta, Hind Leg Kicker value increases over
time)

### Full AI Library Entries

```python
# Add to CARD_EFFECTS_LIBRARY in prompts.py

"Surge": {
    "type": "Action",
    "effect": "Gain 1 CC",
    "strategic_use": "FREE CC - Use when you need 1 more CC for a key play. Lower value than Rush but playable on turn 1.",
    "threat_level": "LOW - Small CC advantage for opponent"
},
"Dwumm": {
    "type": "Toy",
    "effect": "Continuous: All your Toys get +2 Speed",
    "strategic_use": "SPEED ADVANTAGE - Makes your cards strike first in tussles. Combine with strong attackers for one-shot kills.",
    "threat_level": "HIGH - Opponent's cards will strike first against yours"
},
"Twombon": {
    "type": "Toy",
    "effect": "Continuous: All your Toys get +2 Strength",
    "strategic_use": "FORCE MULTIPLIER - Like Ka but cheaper with weaker stats. Good budget option for strength boost.",
    "threat_level": "HIGH - Boosts opponent's entire board"
},
"Drop": {
    "type": "Action",
    "effect": "Target: Sleep any card in play (yours or opponent's)",
    "strategic_use": "PRECISION REMOVAL - Sleep a specific threat. Cheaper than Clean but only one target. Triggers when-sleeped effects!",
    "threat_level": "HIGH - Can sleep your best card"
},
"Jumpscare": {
    "type": "Action",
    "effect": "Target: Return any card in play to owner's hand (no sleep trigger)",
    "strategic_use": "TEMPO BOUNCE - Return a threat without triggering when-sleeped. Great vs Umbruh! Opponent must replay the card.",
    "threat_level": "MEDIUM - Can bounce your key card back to hand"
},
"Sock Sorcerer": {
    "type": "Toy",
    "effect": "Continuous: All your Toys are immune to opponent's card effects",
    "strategic_use": "TEAM PROTECTION - Protects ALL your cards from Twist, Clean, Copy, Drop, etc. Very powerful defensive anchor!",
    "threat_level": "CRITICAL - Your Action cards won't affect opponent's board while in play"
},
"VeryVeryAppleJuice": {
    "type": "Action",
    "effect": "This turn only: All your Toys get +1 Speed, +1 Strength, +1 Stamina",
    "strategic_use": "COMBAT BUFF - Use BEFORE tussling to win fights you'd otherwise lose. One turn only - use it or lose it!",
    "threat_level": "MEDIUM - Temporary boost makes opponent's tussles stronger this turn"
},
"Belchaletta": {
    "type": "Toy",
    "effect": "Triggered: At start of your turn, gain 2 CC",
    "strategic_use": "CC ENGINE - Generates 2 extra CC every turn (6 total per turn!). Huge value if it survives. Priority removal target.",
    "threat_level": "HIGH - Opponent gains +2 CC per turn on top of normal 4"
},
"Hind Leg Kicker": {
    "type": "Toy",
    "effect": "Triggered: When you play another card, gain 1 CC",
    "strategic_use": "CC REFUND - Each card you play refunds 1 CC. Great for combo turns with many plays. Weak stats - protect it!",
    "threat_level": "MEDIUM - Opponent gets partial CC refund on plays"
},

```text

---

## CSV Updates Required

**File:** `backend/data/cards.csv` (merge from beta file)

```csv
Surge,Beta,0,Gain 1 CC.,,,,,,#e612d0,#e612d0,gain_cc:1
Dwumm,Beta,1,Your cards have 2 more speed.,2,2,2,,,#eb9113,#eb9113,stat_boost:speed:2
Twombon,Beta,1,Your cards have 2 more strength.,2,2,2,,,#eb9113,#eb9113,stat_boost:strength:2
Drop,Beta,1,Sleep a card that is in play.,,,,,,#e612d0,#e612d0,sleep_target:1
Jumpscare,Beta,0,Put a card that is in play into their owner's hand.,,,,,,#e612d0,#e612d0,return_target_to_hand:1
Sock Sorcerer,Beta,3,Your opponent's cards' effects don't affect your cards.,3,3,5,,,#eb9113,#eb9113,team_opponent_immunity
VeryVeryAppleJuice,Beta,0,"This turn, your cards have 1 more of each stat.",,,,,,#e612d0,#e612d0,turn_stat_boost:all:1
Belchaletta,Beta,1,"At the start of your turn, gain 2 charge.",3,3,4,,,#eb9113,#eb9113,start_of_turn_gain_cc:2
Hind Leg Kicker,Beta,1,"When you play a card (not this one), gain 1 charge.",3,3,1,,,#eb9113,#eb9113,on_card_played_gain_cc:1

```text

---

## Documentation Updates

After implementation is complete:

1. **Update `EFFECT_SYSTEM_ARCHITECTURE.md`** with new effect types
1. **Create `HOW_TO_ADD_NEW_CARDS.md`** guide covering:
- Using existing effect patterns
- Creating new effect types
- Adding AI awareness
- Writing tests
1. **Update `README.md`** if card count changes significantly

---

## Summary

| Phase | Cards | Files Modified | New Classes | Est. Time |
|-------|-------|----------------|-------------|-----------|
| 1 | Surge, Dwumm, Twombon | CSV, prompts.py | None | 1-2 hrs |
| 2 | Drop, Jumpscare | action_effects.py, effect_registry.py | 2 | 2-3 hrs |
| 3 | Sock Sorcerer | continuous_effects.py, game_state.py | 1 | 2-3 hrs |
| 4 | VeryVeryAppleJuice | action_effects.py, game_engine.py | 1 | 3-4 hrs |
| 5 | Belchaletta, Hind Leg Kicker | continuous_effects.py, game_engine.py, base_effect.py | 2 | 4-5 hrs |

**Total Estimated Time:** 12-17 hours across multiple sessions

---

## Next Steps

1. Review this plan and confirm priorities
1. Start with Phase 1 (easiest cards)
1. Test each batch locally before moving to next phase
1. Create PRs after each phase is complete
1. Document patterns for future card additions

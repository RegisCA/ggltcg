# Adding New Cards to GGLTCG

This guide provides a complete checklist for adding new cards to the game. Following all steps ensures the card works correctly in gameplay, tests pass, and the AI can play the card strategically.

## Quick Reference Checklist

Use this checklist when adding new cards:

- [ ] **Step 1**: Add card to `backend/data/cards.csv`
- [ ] **Step 2**: Add effect handler(s) if needed
- [ ] **Step 3**: Add card to `backend/src/game_engine/ai/prompts.py`
- [ ] **Step 4**: Write comprehensive tests
- [ ] **Step 5**: Run full test suite
- [ ] **Step 6**: Playtest the card

---

## Step 1: Add Card to CSV

**File**: `backend/data/cards.csv`

Add a new row with all required fields. The canonical header (as of December 2025) is:

```csv
name,status,cost,effect,speed,strength,stamina,faction,quote,primary_color,accent_color,effects
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique card name |
| `status` | ✅ | Status code (18 = active) |
| `cost` | ✅ | CC cost to play (0–5 typical) |
| `effect` | ✅ | Human-readable effect description (shown in UI) |
| `speed` | Toys only | Speed stat for tussles |
| `strength` | Toys only | Strength stat for tussles |
| `stamina` | Toys only | Base stamina (health) |
| `faction` | Optional | Reserved for future set/faction metadata |
| `quote` | Optional | Flavor text |
| `primary_color` | ✅ | Hex color for card display |
| `accent_color` | ✅ | Hex color for card accent |
| `effects` | ✅ | Machine-readable effect code(s) used by the effect system |

### Effect Definitions Syntax

Effect definitions are semicolon-separated for multiple effects:

```python
single_effect:param1:param2
effect1;effect2;effect3
```

> **Tip**: Use constants from `backend/src/game_engine/effects_constants.py` for type-safe
> effect definitions. This module provides constants like `EffectDefinitions.OPPONENT_IMMUNITY`
> and helper methods like `EffectDefinitions.stat_boost('strength', 2)` to avoid typos.

### Available Effect Types (from `EffectFactory`)

#### Stat Boosts (Continuous)

- `stat_boost:strength:N` – Your Toys get +N strength
- `stat_boost:speed:N` – Your Toys get +N speed
- `stat_boost:stamina:N` – Your Toys get +N stamina
- `stat_boost:all:N` – Your Toys get +N to all stats

#### Temporary Boosts

- `turn_stat_boost:all:N` – This turn only, +N to all stats

#### CC Effects

- `gain_cc:N` – Gain N CC when played
- `gain_cc:N:not_first_turn` – Gain N CC (cannot play on your first turn)
- `start_of_turn_gain_cc:N` – Gain N CC at start of your turn
- `on_card_played_gain_cc:N` – Gain N CC when you play another card
- `gain_cc_when_sleeped:N` – Gain N CC when this card is sleeped from play

#### Targeting Effects

- `sleep_target:N` – Sleep N target card(s) in play
- `return_target_to_hand:N` – Return N target card(s) to owner's hand

#### Protection Effects

- `opponent_immunity` – This card is immune to opponent's effects
- `team_opponent_immunity` – All your cards are immune to opponent's effects

#### Combat Modifiers

- `auto_win_tussle_on_own_turn` – This card wins all tussles it enters on your turn
- `set_tussle_cost:N` – Your tussles cost N CC
- `set_self_tussle_cost:N:not_turn_1` – This card's tussles cost N CC, but not on turn 1
- `cannot_tussle` – This card cannot initiate tussles

#### Special Effects

- `sleep_all` – Sleep all Toys in play
- `return_all_to_hand` – Return all cards in play to owners' hands
- `copy_card` – Action: copy the effects of another card
- `take_control` – Action: take control of an opponent's Toy
- `return_all_to_hand` – Return all cards in play to owners' hands
- `sleep_target:N` – Sleep N target card(s) in play
- `return_target_to_hand:N` – Return N target card(s) to owner's hand
- `start_of_turn_gain_cc:N` – Gain N CC at start of your turn
- `on_card_played_gain_cc:N` – Gain N CC when you play another card
- `turn_stat_boost:all:N` – This turn only, +N to all stats

#### Cost Modifiers

- `reduce_cost_by_sleeping` – Cost reduced by 1 per card in your sleep zone
- `alternative_cost_sleep_card` – May sleep one of your cards instead of paying CC
- `opponent_cost_increase:N` – Opponent's cards cost N more CC to play

> If you introduce a new effect string that is not yet parsed in
> `EffectFactory.parse_effects`, you **must** add a parser there as part of
> the same change.

### Example Cards

**Action Card (simple)**:

```csv
Surge,18,0,Gain 1 CC.,,,,#e612d0,#e612d0,gain_cc:1
```

**Toy Card (stat boost)**:

```csv
Drum,18,1,Your cards have 2 more speed.,1,3,2,#eb9113,#eb9113,stat_boost:speed:2
```

**Toy Card (triggered effect)**:

```csv
Belchaletta,18,1,"At the start of your turn, gain 2 charge.",3,3,4,#eb9113,#eb9113,start_of_turn_gain_cc:2
```

---

## Step 2: Add Effect Handler (If Needed)

If your card uses a **new effect type** not listed above, you need to
implement it in the existing data-driven effect system.

### 2a. Extend `EffectFactory`

**File**: `backend/src/game_engine/rules/effects/effect_registry.py`

Add a new branch in `EffectFactory.parse_effects` that recognizes your
effect string and dispatches to a dedicated parser, e.g.:

```python
elif effect_type == "my_new_effect":
    effect = cls._parse_my_new_effect(parts, source_card)
    effects.append(effect)
```

### 2b. Create Effect Class

Choose the appropriate base class:

| Base Class | When to Use |
|------------|-------------|
| `PlayEffect` | Effect triggers when card is played |
| `ContinuousEffect` | Effect is always active while in play |
| `TriggeredEffect` | Effect triggers on specific game events |
| `ActivatedEffect` | Player can activate effect by paying cost |

```python
class MyNewEffect(PlayEffect):
    """Description of what this effect does."""

    def __init__(self, source_card: Card, param: int):
        super().__init__(source_card)
        self.param = param

    def apply(self, game_state: GameState, **kwargs: Any) -> None:
        # Implementation here
        ...

    def requires_targets(self) -> bool:
        return False  # or True if targeting

    def get_valid_targets(self, game_state: GameState, **kwargs: Any) -> List[Card]:
        return []  # Return valid target cards if requires_targets is True
```

### 2c. Register Effect in Effect Registry

**File**: `backend/src/game_engine/rules/effects/effect_registry.py`

Import and add to the registry if using class-based effects.

---

## Step 3: Add to AI Prompts

**File**: `backend/src/game_engine/ai/prompts.py`

Add entry to `CARD_EFFECTS_LIBRARY`:

```python
CARD_EFFECTS_LIBRARY = {
    # ... existing cards ...
    
    "MyNewCard": {
        "type": "Toy",  # or "Action"
        "effect": "Description of effect for AI understanding",
        "strategic_use": "CATEGORY - When and why to play this card strategically.",
        "threat_level": "HIGH/MEDIUM/LOW - How dangerous is this card when opponent has it"
    },
}
```

### Strategic Use Categories

Use these prefixes for consistency:

- `FORCE MULTIPLIER` - Boosts other cards
- `CC ENGINE` - Generates CC advantage
- `PROTECTION` - Defensive capability
- `BOARD WIPE` - Clears multiple cards
- `PRECISION REMOVAL` - Removes specific threats
- `TEMPO BOUNCE` - Disrupts opponent's board
- `COMBO ENABLER` - Works well with other cards
- `FINISHER` - Helps close out games

### Threat Levels

- `CRITICAL` - Must deal with immediately (Twist, Clean, Sock Sorcerer)
- `HIGH` - Significant board impact (Ka, stat boosters, CC generators)
- `MEDIUM` - Solid value but manageable
- `LOW` - Minor impact

---

## Step 4: Write Tests

**File**: `backend/tests/test_<card_name>.py` or add to existing test file

### Minimum Test Coverage

1. **Basic play test** - Card can be played and effect applies
2. **Effect verification** - Effect does what it should
3. **Edge cases** - Empty board, no valid targets, etc.
4. **Interaction tests** - How it works with protection (Beary, Knight, Sock Sorcerer)

### Test Template

```python
import pytest
from conftest import create_game_with_cards

class TestMyNewCard:
    """Tests for MyNewCard."""
    
    def test_basic_play(self):
        """MyNewCard can be played and effect applies."""
        setup, cards = create_game_with_cards(
            player1_hand=["MyNewCard"],
            player1_in_play=["Ka"],
            active_player="player1",
            player1_cc=5,
        )
        
        my_card = cards["p1_hand_MyNewCard"]
        
        # Play the card
        setup.engine.play_card(setup.player1, my_card)
        
        # Verify effect
        assert some_expected_condition
    
    def test_interaction_with_protection(self):
        """MyNewCard respects opponent immunity."""
        setup, cards = create_game_with_cards(
            player1_hand=["MyNewCard"],
            player2_in_play=["Beary"],  # Has opponent_immunity
            active_player="player1",
        )
        
        # Test that protected cards aren't affected
        ...
```

### Using Test Fixtures

Always use `create_game_with_cards` from `conftest.py`:

```python
setup, cards = create_game_with_cards(
    player1_hand=["Card1", "Card2"],
    player1_in_play=["Card3"],
    player1_sleep=["Card4"],
    player2_hand=["Card5"],
    player2_in_play=["Card6"],
    active_player="player1",  # or "player2"
    player1_cc=5,  # Optional, default 10
    player2_cc=3,  # Optional, default 10
)

# Access cards by key: p{1|2}_{zone}_{CardName}
card = cards["p1_hand_Card1"]
```

---

## Step 5: Run Full Test Suite

```bash
cd /path/to/ggltcg
source .venv/bin/activate
pytest backend/tests/ -v
```

### Common Test Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Expected N cards, got M` | Card count changed | Run `scripts/validate_new_cards.py` |
| `Unknown effect` | Effect not registered | Check effect_definitions spelling |
| `Card not found` | Card name mismatch | Verify CSV name matches test |

---

## Step 6: Playtest

1. Start backend: `cd backend && python run_server.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`
4. Play several games with the new card
5. Verify:
   - Card displays correctly
   - Effect triggers at right time
   - AI plays the card reasonably
   - No console errors

---

## Validation Script

Run the validation script to catch common issues:

```bash
python scripts/validate_new_cards.py
```

This checks:

- All CSV cards have prompts.py entries
- All effect_definitions are recognized
- No orphaned test files
- Card count matches expected

---

## Troubleshooting

### Card doesn't appear in game

1. Check `status` field is `18` (active)
2. Verify CSV has no syntax errors (commas in text need quotes)
3. Restart backend server

### Effect doesn't work

1. Check `effect_definitions` spelling exactly matches handler
2. Verify effect handler is properly registered
3. Add logging to effect's `apply()` method
4. Check if protection effects are blocking it

### AI doesn't play card well

1. Verify `prompts.py` entry exists
2. Check `strategic_use` gives clear guidance
3. Test if AI understands when card is valuable

### Tests fail after adding card

1. Run `scripts/validate_new_cards.py`
2. Check if `test_card_loader.py` needs updated count
3. Verify test fixtures use correct card names

---

## Files Modified When Adding Cards

| File | Always? | Purpose |
|------|---------|---------|
| `backend/data/cards.csv` | ✅ | Card definition |
| `backend/src/game_engine/ai/prompts.py` | ✅ | AI strategic guidance |
| `backend/tests/test_*.py` | ✅ | Unit tests |
| `backend/src/game_engine/rules/effects/*.py` | If new effect | Effect implementation |

---

## Example: Adding a Simple Card

Let's add "Zap" - an Action that deals 1 damage to a target.

### 1. CSV Entry

```csv
Zap,18,1,Deal 1 damage to target card.,,,,#ff0000,#ff0000,damage_target:1
```

### 2. Effect Handler (if `damage_target` is new)

```python
class DamageTargetEffect(PlayEffect):
    def __init__(self, amount: int):
        self.amount = amount
    
    def apply(self, game_state, card, player, **kwargs):
        target = kwargs.get('target')
        if target:
            target.apply_damage(self.amount)
    
    def requires_targets(self) -> bool:
        return True
    
    def get_valid_targets(self, game_state, card, player):
        opponent = game_state.get_opponent(player.player_id)
        return [c for c in opponent.in_play if c.is_toy()]
```

### 3. Prompts Entry

```python
"Zap": {
    "type": "Action",
    "effect": "Target: Deal 1 damage to any Toy in play",
    "strategic_use": "PRECISION DAMAGE - Finish off wounded cards or weaken targets before tussles.",
    "threat_level": "MEDIUM - Can snipe your weakened cards"
},
```

### 4. Test

```python
def test_zap_deals_damage(self):
    setup, cards = create_game_with_cards(
        player1_hand=["Zap"],
        player2_in_play=["Ka"],
        active_player="player1",
    )
    
    zap = cards["p1_hand_Zap"]
    ka = cards["p2_inplay_Ka"]
    initial_stamina = ka.current_stamina
    
    setup.engine.play_card(setup.player1, zap, target_ids=[ka.id])
    
    assert ka.current_stamina == initial_stamina - 1
```

---

## Related Documentation

- [EFFECT_SYSTEM_ARCHITECTURE.md](./EFFECT_SYSTEM_ARCHITECTURE.md) - Deep dive into effect system
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [coding.instructions.md](../../.github/instructions/coding.instructions.md) - Coding standards
- [testing.instructions.md](../../.github/instructions/testing.instructions.md) - Testing patterns

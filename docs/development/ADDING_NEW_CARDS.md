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

Add a new row with all required fields:

```csv
name,status,cost,effect_text,speed,strength,stamina,primary_color,accent_color,effect_definitions
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique card name |
| `status` | ✅ | Status code (18 = active) |
| `cost` | ✅ | CC cost to play (0-5 typical) |
| `effect_text` | ✅ | Human-readable effect description |
| `speed` | Toys only | Speed stat for tussles |
| `strength` | Toys only | Strength stat for tussles |
| `stamina` | Toys only | Base stamina (health) |
| `primary_color` | ✅ | Hex color for card display |
| `accent_color` | ✅ | Hex color for card accent |
| `effect_definitions` | ✅ | Machine-readable effect code(s) |

### Effect Definitions Syntax

Effect definitions are semicolon-separated for multiple effects:

```
single_effect:param1:param2
effect1;effect2;effect3
```

### Available Effect Types

#### Stat Boosts (Continuous)
- `stat_boost:strength:N` - Your Toys get +N strength
- `stat_boost:speed:N` - Your Toys get +N speed
- `stat_boost:stamina:N` - Your Toys get +N stamina
- `stat_boost:all:N` - Your Toys get +N to all stats

#### Temporary Boosts
- `turn_stat_boost:all:N` - This turn only, +N to all stats

#### CC Effects
- `gain_cc:N` - Gain N CC when played
- `gain_cc:N:not_first_turn` - Gain N CC (cannot play on turn 1)
- `start_of_turn_gain_cc:N` - Gain N CC at start of your turn
- `on_card_played_gain_cc:N` - Gain N CC when you play another card
- `gain_cc_when_sleeped:N` - Gain N CC when this card is sleeped

#### Targeting Effects
- `sleep_target:N` - Sleep N target card(s) in play
- `return_target_to_hand:N` - Return N target card(s) to owner's hand
- `unsleep_target:N` - Return N card(s) from sleep zone to hand

#### Protection Effects
- `opponent_immunity` - This card immune to opponent's effects
- `team_opponent_immunity` - All your cards immune to opponent's effects

#### Combat Modifiers
- `auto_win_tussle_on_own_turn` - Win all tussles on your turn
- `set_tussle_cost:N` - Your tussles cost N CC
- `cannot_tussle` - This card cannot initiate tussles
- `free_tussle;no_tussle_turn_1` - Tussles cost 0, but not on turn 1

#### Special Effects
- `sleep_all` - Sleep all Toys in play
- `return_all_to_hand` - Return all cards in play to owners' hands
- `cascade_sleep:N` - When sleeped, sleep N other cards
- `remove_stamina_ability:N` - Activated ability: spend N CC to remove 1 stamina

#### Cost Modifiers
- `cost_reduction_per_sleep:N` - Cost reduced by N per card in your sleep zone
- `alternative_cost_sleep_toy` - Can sleep a Toy instead of paying CC

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

If your card uses a **new effect type** not listed above, you need to implement it.

### 2a. Create Effect Handler

**File**: `backend/src/game_engine/rules/effects/data_driven_effects.py`

Add parsing logic in `EffectFactory.create_effects_from_definition()`:

```python
elif effect_type == "my_new_effect":
    param = int(parts[1]) if len(parts) > 1 else 1
    effects.append(MyNewEffect(param))
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
    
    def __init__(self, param: int):
        self.param = param
    
    def apply(self, game_state: GameState, card: Card, player: Player, **kwargs) -> None:
        # Implementation here
        pass
    
    def requires_targets(self) -> bool:
        return False  # or True if targeting
    
    def get_valid_targets(self, game_state: GameState, card: Card, player: Player) -> List[Card]:
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

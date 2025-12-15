---
applyTo: 'backend/tests/**/*.py'
description: "Testing standards and patterns for GGLTCG backend tests"
---

# GGLTCG Testing Instructions

## Test Fixtures (conftest.py)

Always use the shared fixtures in `backend/tests/conftest.py` for game setup:

```python
from conftest import create_game_with_cards, create_basic_game, steal_card, GameSetup

# Create a game with specific cards
setup, cards = create_game_with_cards(
    player1_hand=["Sun", "Wake"],
    player1_in_play=["Ka"],
    player1_sleep=["Demideca"],
    player2_in_play=["Knight", "Beary"],
    active_player="player1",
    player1_cc=5,  # Optional, default 10
)

# Access components
setup.engine       # GameEngine instance
setup.game_state   # GameState instance
setup.player1      # Player 1
setup.player2      # Player 2

# Access created cards by key pattern: p{1|2}_{zone}_{CardName}
ka = cards["p1_inplay_Ka"]
knight = cards["p2_inplay_Knight"]
sun = cards["p1_hand_Sun"]
```

### Simulating Stolen Cards

Use `steal_card()` to simulate Twist effect:

```python
# Card owned by P1, controlled by P2
steal_card(setup.game_state, original_card, setup.player2.player_id)
# original_card.owner == "player1"
# original_card.controller == "player2"
```

## Method Signatures

### Tussle

```python
# CORRECT argument order
engine.initiate_tussle(attacker, defender, player)

# NOT this (common mistake)
engine.initiate_tussle(player, attacker, defender)  # WRONG!
```

### Play Card

```python
# With targets (for Sun, Wake, Twist, etc.)
engine.play_card(player, card, target_ids=[card1.id, card2.id])

# With alternative cost (for Ballaber)
engine.play_card(player, card, alternative_cost_card_id=cost_card.id)

# With single target (for Copy, Twist)
engine.play_card(player, card, target_ids=[target.id])
```

## Test Organization

### File Naming

- `test_<feature>.py` - Feature-specific tests
- `test_issues_<numbers>.py` - Bug regression tests (reference GitHub issues)
- `test_<card_name>.py` - Card-specific complex tests

### Test Class Structure

```python
class TestIssue123FeatureName:
    """
    Issue #123: Brief description of the bug.
    
    Detailed explanation of:
    1. What was happening wrong
    2. What the expected behavior is
    3. How to reproduce
    """
    
    def test_specific_scenario(self):
        """One sentence describing what this specific test verifies."""
        # Arrange
        setup, cards = create_game_with_cards(...)
        
        # Act
        result = setup.engine.some_action(...)
        
        # Assert
        assert expected_condition, "Clear error message explaining failure"
```

## Test Card Helpers

For frequently-used cards, use the pre-configured helper functions in `conftest.py`:

```python
from conftest import (
    create_beary, create_knight, create_dream, create_gibbers,
    create_ka, create_demideca, create_copy, create_rush,
    create_surge, create_clean, create_wake, create_wizard,
    create_archer, create_ballaber, create_twist
)

# Create cards with correct stats and effects from CSV
beary = create_beary(owner="player1", zone=Zone.IN_PLAY)
ka = create_ka(owner="player2")
```

These helpers ensure cards have correct effect definitions and stats without manual lookup.

## Common Test Patterns

### Testing Tussle Outcomes

```python
def test_tussle_outcome(self):
    setup, cards = create_game_with_cards(
        player1_in_play=["Ka"],
        player2_in_play=["Demideca"],
        active_player="player1",
    )
    
    attacker = cards["p1_inplay_Ka"]
    defender = cards["p2_inplay_Demideca"]
    
    # Execute tussle
    setup.engine.initiate_tussle(attacker, defender, setup.player1)
    
    # Check results
    assert defender in setup.player2.sleep_zone, "Defender should be sleeped"
    assert attacker in setup.player1.in_play, "Attacker should survive"
```

### Testing Protection Effects

```python
def test_beary_protected_from_opponent_effect(self):
    setup, cards = create_game_with_cards(
        player1_hand=["Clean"],
        player2_in_play=["Beary"],
        active_player="player1",
    )
    
    clean = cards["p1_hand_Clean"]
    beary = cards["p2_inplay_Beary"]
    
    setup.engine.play_card(setup.player1, clean)
    
    # Beary should NOT be sleeped (opponent immunity)
    assert beary in setup.player2.in_play, "Beary should be protected"
```

### Testing Stolen Card Behavior

```python
def test_stolen_card_sleeps_to_owner(self):
    setup, cards = create_game_with_cards(
        player1_in_play=["Ka"],
        active_player="player1",
    )
    
    # Create stolen card (owned by P1, controlled by P2)
    umbruh = create_card("Umbruh", owner="player1")
    umbruh = steal_card(setup.game_state, umbruh, setup.player1, setup.player2)
    
    # Tussle: P1's Ka attacks P2's controlled (but P1-owned) Umbruh
    setup.engine.initiate_tussle(cards["p1_inplay_Ka"], umbruh, setup.player1)
    
    # Umbruh should go to OWNER's (P1) sleep zone, not controller's (P2)
    assert umbruh in setup.player1.sleep_zone
    assert umbruh not in setup.player2.sleep_zone
```

## Key Concepts to Test

### Owner vs Controller

- **Owner**: Original card owner (never changes)
- **Controller**: Who currently controls the card (changes via Twist)
- Cards always sleep to **owner's** zone
- Effects check **controller** for "your cards" / "opponent's cards"

### Effect Timing

1. Card effect resolves
2. State-based actions checked (0 stamina → sleep)
3. Victory condition checked
4. Turn continues

### Protection Hierarchy

- `opponent_immunity` (Beary) blocks effects from opponent-controlled cards
- Knight's auto-win IS an effect and CAN be blocked by Beary
- Tussle damage is NOT an effect (Beary can still take damage)

## Anti-Patterns to Avoid

### ❌ Don't Create Cards Manually in Tests

```python
# BAD - misses effect registration, wrong stats
card = Card(name="Ka", card_type=CardType.TOY, ...)

# GOOD - uses CSV data, proper initialization
setup, cards = create_game_with_cards(player1_in_play=["Ka"])
ka = cards["p1_inplay_Ka"]
```

### ❌ Don't Use Card Names for Lookups

```python
# BAD - multiple cards can have same name
card = next(c for c in player.in_play if c.name == "Ka")

# GOOD - use IDs
card = game_state.find_card_by_id(card_id)
```

### ❌ Don't Bypass GameEngine

```python
# BAD - bypasses effect triggers
player.sleep_zone.append(card)
player.in_play.remove(card)

# GOOD - uses proper game logic
engine._sleep_card(card, owner, was_in_play=True)
```

## Running Tests

```bash
# All tests
cd backend && pytest tests/ -v

# Specific test file
pytest tests/test_issues_131_to_145.py -v

# Specific test class
pytest tests/test_issues_131_to_145.py::TestIssue131KnightVsBeary -v

# Specific test
pytest tests/test_issues_131_to_145.py::TestIssue131KnightVsBeary::test_knight_attacks_beary_both_should_sleep -v

# With short traceback
pytest tests/ -v --tb=short
```

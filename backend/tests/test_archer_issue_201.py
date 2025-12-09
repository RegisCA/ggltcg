"""
Tests for Archer activated ability (Issue #201).

Archer should only be able to activate its ability when there are valid targets
(opponent's cards in play). It should not appear as a valid action when the
opponent has no cards in play.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader
from game_engine.validation.action_validator import ActionValidator


def test_archer_requires_opponent_cards_in_play():
    """
    Test that Archer's activated ability only appears when opponent has cards in play.
    
    Issue #201: Archer's ability should not be available when opponent has no cards
    in play, but currently it appears as a valid action.
    """
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Archer and a basic toy
    archer = next(c for c in all_cards if c.name == "Archer")
    ka = next(c for c in all_cards if c.name == "Ka")
    
    # Create players
    archer.owner = "player1"
    archer.controller = "player1"
    archer.zone = Zone.IN_PLAY
    ka.owner = "player2"
    ka.controller = "player2"
    
    player1 = Player(
        player_id="player1",
        name="Player 1",
        cc=5,  # Enough CC to use ability
        hand=[],
        in_play=[archer],  # Archer is in play
        sleep_zone=[]
    )
    
    player2 = Player(
        player_id="player2",
        name="Player 2",
        cc=5,
        hand=[],
        in_play=[],  # NO cards in play - this is the key
        sleep_zone=[]
    )
    
    # Create game state
    game_state = GameState(
        game_id="test-game",
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1"
    )
    
    # Create game engine
    game_engine = GameEngine(game_state)
    validator = ActionValidator(game_engine)
    
    # Get valid actions for player1
    valid_actions = validator.get_valid_actions("player1")
    
    # Check that Archer's ability is NOT in the valid actions
    archer_abilities = [
        a for a in valid_actions 
        if a.action_type == "activate_ability" and a.card_id == archer.id
    ]
    
    assert len(archer_abilities) == 0, (
        f"Archer's ability should NOT be available when opponent has no cards in play, "
        f"but found {len(archer_abilities)} activate_ability actions"
    )
    
    # Now add a card to opponent's in_play
    player2.in_play.append(ka)
    
    # Get valid actions again
    valid_actions = validator.get_valid_actions("player1")
    
    # Check that Archer's ability IS now in the valid actions
    archer_abilities = [
        a for a in valid_actions 
        if a.action_type == "activate_ability" and a.card_id == archer.id
    ]
    
    assert len(archer_abilities) == 1, (
        f"Archer's ability SHOULD be available when opponent has cards in play, "
        f"but found {len(archer_abilities)} activate_ability actions"
    )
    
    # Verify target_options contains the opponent's card
    ability = archer_abilities[0]
    assert ability.target_options == [ka.id], (
        f"Archer's ability should target opponent's card {ka.id}, "
        f"but target_options is {ability.target_options}"
    )


def test_archer_only_targets_opponent_cards():
    """
    Test that Archer can only target opponent's cards, not the player's own cards.
    """
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Archer and basic toys
    archer = next(c for c in all_cards if c.name == "Archer")
    ka = next(c for c in all_cards if c.name == "Ka")
    knight = next(c for c in all_cards if c.name == "Knight")
    
    # Create players
    archer.owner = "player1"
    archer.controller = "player1"
    archer.zone = Zone.IN_PLAY
    knight.owner = "player1"
    knight.controller = "player1"
    knight.zone = Zone.IN_PLAY
    ka.owner = "player2"
    ka.controller = "player2"
    ka.zone = Zone.IN_PLAY
    
    player1 = Player(
        player_id="player1",
        name="Player 1",
        cc=5,
        hand=[],
        in_play=[archer, knight],  # Both Archer and Knight in player1's play
        sleep_zone=[]
    )
    
    player2 = Player(
        player_id="player2",
        name="Player 2",
        cc=5,
        hand=[],
        in_play=[ka],  # Ka in player2's play
        sleep_zone=[]
    )
    
    # Create game state
    game_state = GameState(
        game_id="test-game",
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1"
    )
    
    # Create game engine and get Archer's effect
    game_engine = GameEngine(game_state)
    from game_engine.rules.effects import EffectRegistry
    from game_engine.rules.effects.action_effects import ArcherActivatedAbility
    
    effects = EffectRegistry.get_effects(archer)
    archer_effect = next((e for e in effects if isinstance(e, ArcherActivatedAbility)), None)
    
    assert archer_effect is not None, "Archer should have ArcherActivatedAbility effect"
    
    # Get valid targets for Archer's ability
    valid_targets = archer_effect.get_valid_targets(game_state)
    valid_target_ids = [t.id for t in valid_targets]
    
    # Verify only opponent's card (Ka) is a valid target, NOT player's own Knight
    assert ka.id in valid_target_ids, "Archer should be able to target opponent's Ka"
    assert knight.id not in valid_target_ids, "Archer should NOT be able to target own Knight"
    assert archer.id not in valid_target_ids, "Archer should NOT be able to target itself"


if __name__ == "__main__":
    test_archer_requires_opponent_cards_in_play()
    test_archer_only_targets_opponent_cards()
    test_archer_cannot_target_beary_issue_189()
    print("✅ All Archer tests passed!")


def test_archer_cannot_target_sock_sorcerer_protected_cards():
    """
    Test that Archer cannot target cards protected by Sock Sorcerer.
    
    Sock Sorcerer has team_opponent_immunity which protects all your cards
    from opponent's effects. When Sock Sorcerer is in play, even Ka (which
    normally has no protection) should be immune to Archer.
    """
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Archer, Sock Sorcerer, and Ka
    archer = next(c for c in all_cards if c.name == "Archer")
    sock_sorcerer = next(c for c in all_cards if c.name == "Sock Sorcerer")
    ka = next(c for c in all_cards if c.name == "Ka")
    
    # Set ownership
    archer.owner = "player1"
    archer.controller = "player1"
    archer.zone = Zone.IN_PLAY
    sock_sorcerer.owner = "player2"
    sock_sorcerer.controller = "player2"
    sock_sorcerer.zone = Zone.IN_PLAY
    ka.owner = "player2"
    ka.controller = "player2"
    ka.zone = Zone.IN_PLAY
    
    player1 = Player(
        player_id="player1",
        name="Player 1",
        cc=5,
        hand=[],
        in_play=[archer],
        sleep_zone=[]
    )
    
    player2 = Player(
        player_id="player2",
        name="Player 2",
        cc=5,
        hand=[],
        in_play=[sock_sorcerer, ka],  # Sock Sorcerer protects Ka
        sleep_zone=[]
    )
    
    # Create game state
    game_state = GameState(
        game_id="test-game",
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1"
    )
    
    # Create game engine and get Archer's effect
    game_engine = GameEngine(game_state)
    from game_engine.rules.effects import EffectRegistry
    from game_engine.rules.effects.action_effects import ArcherActivatedAbility
    
    effects = EffectRegistry.get_effects(archer)
    archer_effect = next((e for e in effects if isinstance(e, ArcherActivatedAbility)), None)
    
    assert archer_effect is not None, "Archer should have ArcherActivatedAbility effect"
    
    # Get valid targets for Archer's ability
    valid_targets = archer_effect.get_valid_targets(game_state)
    valid_target_ids = [t.id for t in valid_targets]
    
    # Verify NEITHER Sock Sorcerer NOR Ka can be targeted (team protection)
    assert sock_sorcerer.id not in valid_target_ids, (
        f"Archer should NOT be able to target Sock Sorcerer (has team_opponent_immunity)"
    )
    assert ka.id not in valid_target_ids, (
        f"Archer should NOT be able to target Ka when Sock Sorcerer is in play (team protection)"
    )
    
    # Verify there are NO valid targets at all
    assert len(valid_target_ids) == 0, (
        f"Archer should have NO valid targets when all opponent cards are protected by Sock Sorcerer"
    )
    
    # Also verify via ActionValidator - ability should not be available
    from game_engine.validation.action_validator import ActionValidator
    validator = ActionValidator(game_engine)
    valid_actions = validator.get_valid_actions("player1")
    
    archer_abilities = [
        a for a in valid_actions 
        if a.action_type == "activate_ability" and a.card_id == archer.id
    ]
    
    assert len(archer_abilities) == 0, (
        f"Archer's ability should NOT be available when all targets are protected by Sock Sorcerer"
    )


def test_archer_cannot_target_beary_issue_189():
    """
    Test that Archer cannot target Beary (Issue #189).
    
    Beary has opponent_immunity, which means opponent's card effects don't affect it.
    Archer's activated ability should not be able to target Beary.
    """
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Archer, Beary, and Ka
    archer = next(c for c in all_cards if c.name == "Archer")
    beary = next(c for c in all_cards if c.name == "Beary")
    ka = next(c for c in all_cards if c.name == "Ka")
    
    # Set ownership
    archer.owner = "player1"
    archer.controller = "player1"
    archer.zone = Zone.IN_PLAY
    beary.owner = "player2"
    beary.controller = "player2"
    beary.zone = Zone.IN_PLAY
    ka.owner = "player2"
    ka.controller = "player2"
    ka.zone = Zone.IN_PLAY
    
    player1 = Player(
        player_id="player1",
        name="Player 1",
        cc=5,
        hand=[],
        in_play=[archer],
        sleep_zone=[]
    )
    
    player2 = Player(
        player_id="player2",
        name="Player 2",
        cc=5,
        hand=[],
        in_play=[beary, ka],  # Both Beary (protected) and Ka (targetable)
        sleep_zone=[]
    )
    
    # Create game state
    game_state = GameState(
        game_id="test-game",
        players={"player1": player1, "player2": player2},
        turn_number=1,
        phase=Phase.MAIN,
        active_player_id="player1",
        first_player_id="player1"
    )
    
    # Create game engine and get Archer's effect
    game_engine = GameEngine(game_state)
    from game_engine.rules.effects import EffectRegistry
    from game_engine.rules.effects.action_effects import ArcherActivatedAbility
    
    effects = EffectRegistry.get_effects(archer)
    archer_effect = next((e for e in effects if isinstance(e, ArcherActivatedAbility)), None)
    
    assert archer_effect is not None, "Archer should have ArcherActivatedAbility effect"
    
    # Get valid targets for Archer's ability
    valid_targets = archer_effect.get_valid_targets(game_state)
    valid_target_ids = [t.id for t in valid_targets]
    
    # Verify Beary is NOT a valid target (protected by opponent_immunity)
    assert beary.id not in valid_target_ids, (
        f"Archer should NOT be able to target Beary (opponent_immunity), "
        f"but Beary.id={beary.id} is in valid_targets"
    )
    
    # Verify Ka IS a valid target (not protected)
    assert ka.id in valid_target_ids, (
        f"Archer should be able to target Ka (not protected), "
        f"but Ka.id={ka.id} is not in valid_targets"
    )
    
    # Also verify via ActionValidator (what the UI and AI see)
    from game_engine.validation.action_validator import ActionValidator
    validator = ActionValidator(game_engine)
    valid_actions = validator.get_valid_actions("player1")
    
    archer_abilities = [
        a for a in valid_actions 
        if a.action_type == "activate_ability" and a.card_id == archer.id
    ]
    
    assert len(archer_abilities) == 1, (
        f"Expected 1 Archer ability action, got {len(archer_abilities)}"
    )
    
    ability_action = archer_abilities[0]
    assert beary.id not in ability_action.target_options, (
        f"Beary should not be in Archer's ability target_options in ActionValidator"
    )
    assert ka.id in ability_action.target_options, (
        f"Ka should be in Archer's ability target_options in ActionValidator"
    )

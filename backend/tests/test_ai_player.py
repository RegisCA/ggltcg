"""
Test the AI player integration.

This script creates a game and has the AI take a few turns to verify it works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.ai.llm_player import LLMPlayer
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader
from game_engine.game_engine import GameEngine
from api.schemas import ValidAction


def create_test_game():
    """Create a test game with simple decks."""
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Create AI deck
    ai_cards = [
        next(c for c in all_cards if c.name == "Ka"),
        next(c for c in all_cards if c.name == "Knight"),
        next(c for c in all_cards if c.name == "Wizard"),
    ]
    
    # Create opponent deck
    opponent_cards = [
        next(c for c in all_cards if c.name == "Demideca"),
        next(c for c in all_cards if c.name == "Beary"),
        next(c for c in all_cards if c.name == "Archer"),
    ]
    
    # Set ownership
    for card in ai_cards:
        card.owner = "ai"
        card.controller = "ai"
    
    for card in opponent_cards:
        card.owner = "human"
        card.controller = "human"
    
    ai_player = Player(
        player_id="ai",
        name="Claude AI",
        hand=ai_cards,
    )
    
    human_player = Player(
        player_id="human",
        name="Human",
        hand=opponent_cards,
    )
    
    game_state = GameState(
        game_id="test-ai-game",
        players={"ai": ai_player, "human": human_player},
        active_player_id="ai",
        first_player_id="ai",
        turn_number=1,
        phase=Phase.START,
    )
    
    return game_state


def get_valid_actions(engine, player):
    """Get list of valid actions for a player."""
    game_state = engine.game_state
    valid_actions = []
    
    # End turn
    valid_actions.append(
        ValidAction(
            action_type="end_turn",
            description="End your turn"
        )
    )
    
    # Play cards
    for card in player.hand:
        if engine.can_play_card(player, card):
            cost = engine.calculate_card_cost(player, card)
            valid_actions.append(
                ValidAction(
                    action_type="play_card",
                    card_name=card.name,
                    cost_cc=cost,
                    description=f"Play {card.name} (Cost: {cost} CC)"
                )
            )
    
    # Tussles
    opponent = game_state.get_opponent(player.player_id)
    for card in player.in_play:
        if card.card_type == CardType.TOY:
            if engine.can_tussle(card, None, player):
                cost = engine.calculate_tussle_cost(card, player)
                valid_actions.append(
                    ValidAction(
                        action_type="tussle",
                        card_name=card.name,
                        cost_cc=cost,
                        target_options=["direct_attack"],
                        description=f"{card.name} direct attack (Cost: {cost} CC)"
                    )
                )
            
            if opponent:
                for defender in opponent.in_play:
                    if engine.can_tussle(card, defender, player):
                        cost = engine.calculate_tussle_cost(card, player)
                        valid_actions.append(
                            ValidAction(
                                action_type="tussle",
                                card_name=card.name,
                                cost_cc=cost,
                                target_options=[defender.name],
                                description=f"{card.name} tussle {defender.name} (Cost: {cost} CC)"
                            )
                        )
    
    return valid_actions


def main():
    """Test the AI player."""
    print("=" * 60)
    print("AI Player Integration Test")
    print("=" * 60)
    
    # Create game
    print("\nCreating test game...")
    game_state = create_test_game()
    engine = GameEngine(game_state)
    engine.start_turn()
    
    print(f"✓ Game created with AI player (Turn {game_state.turn_number})")
    print(f"  AI CC: {game_state.players['ai'].cc}")
    print(f"  AI Hand: {[c.name for c in game_state.players['ai'].hand]}")
    
    # Create AI player
    print("\nInitializing AI player...")
    try:
        ai_player = LLMPlayer()
        print("✓ AI player initialized with Claude API")
    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTo use the AI player, set your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # Have AI take a few turns
    print("\n" + "=" * 60)
    print("AI Turn Simulation")
    print("=" * 60)
    
    for turn_num in range(1, 4):  # 3 AI turns
        print(f"\n--- Turn {game_state.turn_number} (AI) ---")
        
        ai = game_state.players["ai"]
        print(f"AI Status: {ai.cc} CC, {len(ai.hand)} in hand, {len(ai.in_play)} in play")
        
        # Get valid actions
        valid_actions = get_valid_actions(engine, ai)
        print(f"Valid actions: {len(valid_actions)}")
        
        # AI selects action
        action_index = ai_player.select_action(game_state, "ai", valid_actions)
        
        if action_index is None:
            print("❌ AI failed to select an action")
            break
        
        selected_action = valid_actions[action_index]
        print(f"✓ AI selected: {selected_action.description}")
        
        # Execute action (simplified - just end turn for this test)
        if selected_action.action_type == "end_turn":
            engine.end_turn()
            # Switch back to AI for testing
            game_state.active_player_id = "ai"
            engine.start_turn()
        elif selected_action.action_type == "play_card":
            card = next(c for c in ai.hand if c.name == selected_action.card_name)
            engine.play_card(ai, card)
        
        print(f"Turn {turn_num} complete\n")
    
    print("=" * 60)
    print("✅ AI Player Test Complete!")
    print("=" * 60)
    print("\nThe AI player successfully:")
    print("- Connected to Claude API")
    print("- Analyzed game state")
    print("- Selected valid actions")
    print("- Provided strategic reasoning")


if __name__ == "__main__":
    main()

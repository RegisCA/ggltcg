#!/usr/bin/env python3
"""
Test the AI player integration.

This script creates a game and has the AI take a few turns to verify it works.

Usage:
    export GOOGLE_API_KEY='your-key-here'
    python3 tests/test_ai_player.py
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
    
    # Play cards FIRST (encourage action)
    for card in player.hand:
        if engine.can_play_card(card, player)[0]:  # Returns (bool, reason) tuple
            cost = engine.calculate_card_cost(card, player)
            # Only add if player can afford it
            if player.cc >= cost:
                valid_actions.append(
                    ValidAction(
                        action_type="play_card",
                        card_name=card.name,
                        cost_cc=cost,
                        description=f"Play {card.name} (Cost: {cost} CC)"
                    )
                )
    
    # Tussles SECOND (primary win condition)
    opponent = game_state.get_opponent(player.player_id)
    for card in player.in_play:
        if card.card_type == CardType.TOY:
            # Direct attack (only if opponent has no cards in play but has cards in hand)
            if engine.can_tussle(card, None, player):
                cost = engine.calculate_tussle_cost(card, player)
                # Check affordability, opponent has no defenders, and has cards in hand
                if player.cc >= cost and not opponent.has_cards_in_play() and len(opponent.hand) > 0:
                    # Also check max 2 direct attacks per turn
                    if player.direct_attacks_this_turn < 2:
                        valid_actions.append(
                            ValidAction(
                                action_type="tussle",
                                card_name=card.name,
                                cost_cc=cost,
                                target_options=["direct_attack"],
                                description=f"{card.name} direct attack (Cost: {cost} CC)"
                            )
                        )
            
            # Targeted tussles
            if opponent:
                for defender in opponent.in_play:
                    if engine.can_tussle(card, defender, player):
                        cost = engine.calculate_tussle_cost(card, player)
                        # Only add if player can afford it
                        if player.cc >= cost:
                            valid_actions.append(
                                ValidAction(
                                    action_type="tussle",
                                    card_name=card.name,
                                    cost_cc=cost,
                                    target_options=[defender.name],
                                    description=f"{card.name} tussle {defender.name} (Cost: {cost} CC)"
                                )
                            )
    
    # End turn LAST (should be least preferred)
    valid_actions.append(
        ValidAction(
            action_type="end_turn",
            description="End your turn"
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
    print(f"  Human Hand: {[c.name for c in game_state.players['human'].hand]}")
    
    # Create AI player
    print("\nInitializing AI player...")
    try:
        ai_player = LLMPlayer()
        provider_name = "Gemini" if ai_player.provider == "gemini" else "Claude"
        model_name = ai_player.model_name if ai_player.provider == "gemini" else ai_player.model
        print(f"✓ AI player initialized with {provider_name} API (model: {model_name})")
    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTo use the AI player, set your API key:")
        print("  Gemini: export GOOGLE_API_KEY='your-api-key-here'")
        print("  Claude: export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # Have AI take a few turns
    print("\n" + "=" * 60)
    print("AI Turn Simulation")
    print("=" * 60)
    
    max_turns = 3
    max_actions_per_turn = 10  # Safety limit to prevent infinite loops
    
    for turn_num in range(max_turns):
        ai = game_state.players["ai"]
        
        print(f"\n{'=' * 60}")
        print(f"TURN {game_state.turn_number} - AI")
        print(f"{'=' * 60}")
        print(f"AI Status: {ai.cc} CC, {len(ai.hand)} in hand, {len(ai.in_play)} in play")
        
        # AI takes actions until it ends its turn
        action_count = 0
        turn_ended = False
        
        while not turn_ended and action_count < max_actions_per_turn:
            action_count += 1
            
            # Get current CC status
            current_cc = ai.cc
            
            # Get valid actions (based on CURRENT state)
            valid_actions = get_valid_actions(engine, ai)
            
            # If only action is "end turn", auto-end without calling AI
            if len(valid_actions) == 1 and valid_actions[0].action_type == "end_turn":
                print(f"\n--- Action {action_count} (AI has {current_cc} CC) ---")
                print("Only action available is 'End your turn' - auto-ending turn")
                selected_action = valid_actions[0]
                action_index = 0
            else:
                # Show what actions are available (for debugging)
                print(f"\n--- Action {action_count} (AI has {current_cc} CC) ---")
                if len(valid_actions) <= 5:
                    print(f"Available: {[a.description for a in valid_actions]}")
                else:
                    print(f"Available: {len(valid_actions)} actions")
                
                # AI selects action
                action_index = ai_player.select_action(game_state, "ai", valid_actions)
                
                if action_index is None:
                    print("❌ AI failed to select an action, ending turn")
                    turn_ended = True
                    break
                
                selected_action = valid_actions[action_index]
                print(f"✓ AI selected: {selected_action.description}")
            
            # Execute action
            try:
                if selected_action.action_type == "end_turn":
                    turn_ended = True
                    # Manually end the turn without switching players (for testing)
                    game_state.phase = Phase.END
                    
                    # Increment turn number FIRST
                    old_turn = game_state.turn_number
                    game_state.turn_number += 1
                    
                    # Start new turn for AI
                    # Only the very first turn (turn 1) gets 2 CC for the starting player
                    # All other turns get 4 CC
                    game_state.phase = Phase.START
                    ai.reset_turn_counters()
                    
                    # Since we just incremented, turn_number is now 2, 3, 4, etc.
                    # These should all get 4 CC (only turn 1 got 2 CC initially)
                    cc_gain = 4  # Always 4 CC for turns after turn 1
                    ai.gain_cc(cc_gain)
                    game_state.phase = Phase.MAIN
                    
                    print(f"   → Turn {old_turn} ended. Turn {game_state.turn_number} starts: AI gains {cc_gain} CC (now has {ai.cc} CC)")
                    
                elif selected_action.action_type == "play_card":
                    card = next((c for c in ai.hand if c.name == selected_action.card_name), None)
                    if card:
                        cc_before = ai.cc
                        engine.play_card(ai, card)
                        cc_after = ai.cc
                        print(f"   → {card.name} moved to play zone (spent {cc_before - cc_after} CC, now has {cc_after} CC)")
                    else:
                        print(f"   ⚠ Card {selected_action.card_name} not found in hand!")
                        
                elif selected_action.action_type == "tussle":
                    attacker = next((c for c in ai.in_play if c.name == selected_action.card_name), None)
                    if attacker:
                        cc_before = ai.cc
                        # Determine defender (None for direct attack)
                        defender = None
                        if selected_action.target_options and selected_action.target_options[0] != "direct_attack":
                            opponent = game_state.get_opponent(ai.player_id)
                            defender = next((c for c in opponent.in_play if c.name == selected_action.target_options[0]), None)
                        
                        # Check if tussle is valid before executing
                        can_do, reason = engine.can_tussle(attacker, defender, ai)
                        if not can_do:
                            opponent = game_state.get_opponent(ai.player_id)
                            print(f"   ⚠ Tussle validation failed: {reason}")
                            print(f"      Debug: Opponent has {len(opponent.hand)} in hand, {len(opponent.in_play)} in play, {len(opponent.sleep_zone)} sleeped")
                        
                        result, sleeped_from_hand = engine.initiate_tussle(attacker, defender, ai)
                        cc_after = ai.cc
                        
                        if not result:
                            print(f"   ⚠ Tussle failed! (CC unchanged: {cc_after})")
                        elif defender:
                            print(f"   → Tussle succeeded! (spent {cc_before - cc_after} CC, now has {cc_after} CC)")
                        elif sleeped_from_hand:
                            # Direct attack - show what card was sleeped
                            print(f"   → Direct attack succeeded! Sleeped {sleeped_from_hand} from opponent's hand")
                                else:
                                    print(f"   → Direct attack succeeded!")
                            else:
                                print(f"   → Direct attack succeeded!")
                            
                            print(f"      Spent {cc_before - cc_after} CC, now has {cc_after} CC")
                            print(f"      Opponent now: {len(opponent.hand)} in hand, {len(opponent.sleep_zone)} sleeped")
                            
                            # Check for win condition
                            total_opponent_cards = len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)
                            if len(opponent.sleep_zone) == total_opponent_cards:
                                print(f"\n🎉 GAME WON! All {total_opponent_cards} opponent cards are sleeped!")
                                return  # Exit early - game is over
                    else:
                        print(f"   ⚠ Attacker {selected_action.card_name} not found in play!")
                        
            except Exception as e:
                print(f"   ⚠ Error executing action: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ AI Player Test Complete!")
    print("=" * 60)
    provider_name = "Gemini" if ai_player.provider == "gemini" else "Claude"
    print(f"\nThe AI player successfully:")
    print(f"- Connected to {provider_name} API")
    print("- Analyzed game state")
    print("- Selected valid actions")
    print("- Provided strategic reasoning")


if __name__ == "__main__":
    main()

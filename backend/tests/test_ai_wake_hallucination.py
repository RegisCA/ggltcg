import pytest
import sys
import os
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.turn_planner import TurnPlanner
from ai_test_support import has_valid_ai_api_key, build_turn_planner

# Skip if no API key
def _has_valid_api_key():
    return has_valid_ai_api_key()

pytestmark = pytest.mark.skipif(
    not _has_valid_api_key(),
    reason="No valid AI provider API key found - skipping live LLM tests"
)

class TestWakeHallucination:
    """
    Reproduction of Wake hallucination in Game 31e33312.
    
    Scenario:
    - Turn 2, 4 Charge.
    - Hand: Surge, Wake, Knight, Umbruh, Paper Plane, Archer.
    - Break Zone: Archer (or some other card).
    - Opponent Board: Umbruh, Paper Plane.
    
    Issue: AI plays Wake with target_ids: null.
    """
    
    def test_wake_requires_target(self):
        # Setup game with 4 Charge
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Wake", "Knight", "Umbruh", "Paper Plane", "Archer"],
            player1_in_play=[],
            player1_charge=4,
            player1_break=["Archer"],  # Put something in break zone
            player2_hand=[],
            player2_in_play=["Umbruh", "Paper Plane"],
            player2_charge=1
        )
        game_state = setup.game_state
        
        planner = build_turn_planner()
        
        # Generate plan
        plan = planner.create_plan(game_state, player_id="player1")
        
        print("\nGenerated Plan:")
        for action in plan.action_sequence:
            print(f"- {action.action_type} {action.card_name} (Target: {action.target_ids})")
            
            if action.card_name == "Wake":
                assert action.target_ids is not None, "Wake MUST have a target_id"
                assert len(action.target_ids) == 1, "Wake MUST target exactly 1 card"
                # Verify target is in break zone
                target_id = action.target_ids[0]
                break_zone_ids = [c.id for c in game_state.player1.break_zone]
                assert target_id in break_zone_ids, f"Wake target {target_id} must be in break zone {break_zone_ids}"


import pytest
import sys
import os
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from game_engine.ai.turn_planner import TurnPlanner

# Skip if no API key
def _has_valid_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    return key and not key.startswith("dummy") and len(key) > 20

pytestmark = pytest.mark.skipif(
    not _has_valid_api_key(),
    reason="Valid GOOGLE_API_KEY not set - skipping LLM tests"
)

class TestWakeHallucination:
    """
    Reproduction of Wake hallucination in Game 31e33312.
    
    Scenario:
    - Turn 2, 4 CC.
    - Hand: Surge, Wake, Knight, Umbruh, Paper Plane, Archer.
    - Sleep Zone: Archer (or some other card).
    - Opponent Board: Umbruh, Paper Plane.
    
    Issue: AI plays Wake with target_ids: null.
    """
    
    def test_wake_requires_target(self):
        # Setup game with 4 CC
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Wake", "Knight", "Umbruh", "Paper Plane", "Archer"],
            player1_in_play=[],
            player1_cc=4,
            player1_sleep=["Archer"],  # Put something in sleep zone
            player2_hand=[],
            player2_in_play=["Umbruh", "Paper Plane"],
            player2_cc=1
        )
        game_state = setup.game_state
        
        # Initialize AI
        from google import genai
        api_key = os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
        
        planner = TurnPlanner(client=client, model_name=model, fallback_model=fallback)
        
        # Generate plan
        plan = planner.create_plan(game_state, player_id="player1")
        
        print("\nGenerated Plan:")
        for action in plan.action_sequence:
            print(f"- {action.action_type} {action.card_name} (Target: {action.target_ids})")
            
            if action.card_name == "Wake":
                assert action.target_ids is not None, "Wake MUST have a target_id"
                assert len(action.target_ids) == 1, "Wake MUST target exactly 1 card"
                # Verify target is in sleep zone
                target_id = action.target_ids[0]
                sleep_zone_ids = [c.id for c in game_state.player1.sleep_zone]
                assert target_id in sleep_zone_ids, f"Wake target {target_id} must be in sleep zone {sleep_zone_ids}"


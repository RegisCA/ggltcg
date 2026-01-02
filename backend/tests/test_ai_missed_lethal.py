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

class TestMissedLethal:
    """
    Reproduction of missed optimization in game c453f8ab.
    
    Scenario:
    - Turn 2, 4 CC.
    - Hand: Surge, Knight, Umbruh, Paper Plane, Archer, Wake.
    - Opponent Board: Umbruh.
    
    Missed Line: Surge (+1) -> Knight (1) -> Tussle (2) -> Direct Attack (2).
    Total Cost: 5 CC. Available: 4 + 1 = 5 CC.
    
    Current AI Behavior: Knight (1) -> Tussle (2) -> End Turn (1 CC wasted).
    """
    
    def test_surge_knight_combo_optimization(self):
        # Setup game with 4 CC
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Paper Plane", "Archer", "Wake"],
            player1_in_play=[],
            player1_cc=4,
            player2_hand=[],
            player2_in_play=["Umbruh"],
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
            print(f"- {action.action_type} {action.card_name} (Cost: {action.cc_cost}, After: {action.cc_after})")
        
        # Check if Surge was used
        has_surge = any(a.card_name == "Surge" for a in plan.action_sequence)
        
        # Check if Direct Attack was used
        has_direct_attack = any(a.action_type == "direct_attack" for a in plan.action_sequence)
        
        if not has_surge:
            print("\n❌ FAILED: AI missed Surge optimization!")
        if not has_direct_attack:
            print("\n❌ FAILED: AI missed follow-up Direct Attack!")
            
        assert has_surge, "AI should use Surge to enable the full combo"
        assert has_direct_attack, "AI should use the extra CC for a direct attack"

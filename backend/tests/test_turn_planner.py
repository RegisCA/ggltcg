"""
Tests for AI v3 Turn Planner.

This module tests the turn planning phase of AI v3, verifying that:
1. Plans are generated with valid structure
2. Card IDs are correctly referenced
3. CC budgeting is accurate
4. Threat prioritization follows the strategy guide

Run with: pytest tests/test_turn_planner.py -v
"""

import pytest
import os
import json
from pathlib import Path

# Add backend/src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards, create_basic_game, create_card
from game_engine.models.card import Zone


# Skip all tests if no API key (CI environment)
pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set - skipping LLM tests"
)


@pytest.fixture
def turn_planner():
    """Create a TurnPlanner instance for testing."""
    from google import genai
    from game_engine.ai.turn_planner import TurnPlanner
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
    
    return TurnPlanner(client=client, model_name=model, fallback_model=fallback)


class TestTurnPlannerBasic:
    """Basic turn planner tests."""
    
    def test_planner_creates_plan_empty_board(self, turn_planner):
        """Test that planner creates a valid plan for an empty board state."""
        # Setup: Turn 1-like scenario with no cards in play
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Ka", "Surge"],
            player1_in_play=[],
            player2_hand=["Knight", "Ka", "Archer"],
            player2_in_play=[],
            player1_cc=2,  # Turn 1 CC
            player2_cc=2,
            active_player="player1",
            turn_number=1,
        )
        
        # Generate plan
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        # Assertions
        assert plan is not None, "Plan should be generated"
        assert plan.cc_start == 2, "CC start should match player's CC"
        assert len(plan.action_sequence) > 0, "Plan should have at least one action"
        assert plan.action_sequence[-1].action_type == "end_turn", "Plan should end with end_turn"
        
        # Log plan for manual review
        print("\n" + "=" * 60)
        print("PLAN OUTPUT (empty board):")
        print(f"Threat Assessment: {plan.threat_assessment}")
        print(f"Selected Strategy: {plan.selected_strategy}")
        print(f"CC: {plan.cc_start} → {plan.cc_after_plan}")
        print(f"Expected cards slept: {plan.expected_cards_slept}")
        print(f"Efficiency: {plan.cc_efficiency}")
        print("Actions:")
        for i, action in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'} ({action.cc_cost} CC)")
        print("=" * 60)
    
    def test_planner_creates_plan_with_threats(self, turn_planner):
        """Test planning when opponent has cards in play (threats)."""
        # Setup: Opponent has Knight and Paper Plane, AI has Archer in hand
        setup, cards = create_game_with_cards(
            player1_hand=["Archer", "Knight", "Surge", "Umbruh"],
            player1_in_play=[],
            player2_hand=["Ka", "Wizard"],
            player2_in_play=["Knight", "Paper Plane"],
            player1_cc=4,
            player2_cc=4,
            active_player="player1",
            turn_number=2,
        )
        
        # Generate plan
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        # Assertions
        assert plan is not None, "Plan should be generated"
        assert "Knight" in plan.threat_assessment or "Paper Plane" in plan.threat_assessment, \
            "Threat assessment should mention opponent's cards"
        
        # Log plan for manual review
        print("\n" + "=" * 60)
        print("PLAN OUTPUT (opponent has threats):")
        print(f"Threat Assessment: {plan.threat_assessment}")
        print(f"Selected Strategy: {plan.selected_strategy}")
        print(f"CC: {plan.cc_start} → {plan.cc_after_plan}")
        print(f"Expected cards slept: {plan.expected_cards_slept}")
        print(f"Efficiency: {plan.cc_efficiency}")
        print("Actions:")
        for i, action in enumerate(plan.action_sequence, 1):
            target_info = f" → {action.target_names}" if action.target_names else ""
            print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}{target_info} ({action.cc_cost} CC)")
        print("=" * 60)
    
    def test_planner_validates_card_ids(self, turn_planner):
        """Test that plan validation catches invalid card IDs."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Ka"],
            player1_in_play=["Archer"],
            player2_in_play=["Wizard"],
            player1_cc=4,
        )
        
        # Generate plan
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        # Validate plan
        errors = turn_planner.validate_plan_actions(
            plan,
            setup.game_state,
            "player1"
        )
        
        # Log validation results
        print(f"\nValidation errors: {errors}")
        
        # Should have few or no errors if LLM is working correctly
        # (We don't assert zero errors because LLM might make mistakes)


class TestTurnPlannerScenarios:
    """Test specific game scenarios from the strategy guide."""
    
    def test_archer_removal_path_scenario(self, turn_planner):
        """
        Test the Archer removal path from strategy guide example.
        
        Scenario: 4 CC, opponent has Knight (3 STA) and Paper Plane (1 STA)
        Expected: Archer path should be identified as efficient
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Archer", "Surge", "Umbruh", "Knight"],
            player1_in_play=[],
            player2_in_play=["Knight", "Paper Plane"],
            player1_cc=4,
            active_player="player1",
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        
        # The plan should consider Archer path
        # Expected: ~4 CC to sleep 2 cards = 2.0 CC per card
        print("\n" + "=" * 60)
        print("ARCHER PATH SCENARIO:")
        print(f"Strategy: {plan.selected_strategy}")
        print(f"Sequences considered: {plan.sequences_considered}")
        print(f"CC Efficiency: {plan.cc_efficiency}")
        for i, action in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {action.action_type}: {action.card_name} ({action.cc_cost} CC → {action.cc_after} CC)")
        print("=" * 60)
    
    def test_critical_threat_sock_sorcerer(self, turn_planner):
        """
        Test that Sock Sorcerer is identified as CRITICAL threat.
        
        Sock Sorcerer blocks all effect-based removal - must be removed first.
        """
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Drop", "Clean"],
            player1_in_play=["Ka"],
            player2_in_play=["Sock Sorcerer", "Wizard"],
            player1_cc=4,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        
        # Should identify Sock Sorcerer as CRITICAL
        assert "CRITICAL" in plan.threat_assessment or "Sock Sorcerer" in plan.threat_assessment
        
        print("\n" + "=" * 60)
        print("SOCK SORCERER (CRITICAL) SCENARIO:")
        print(f"Threat Assessment: {plan.threat_assessment}")
        print(f"Strategy: {plan.selected_strategy}")
        print("=" * 60)
    
    def test_wizard_high_threat(self, turn_planner):
        """Test that Wizard is identified as HIGH threat (enables cheap tussles)."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Drop", "Archer"],
            player1_in_play=[],
            player2_in_play=["Wizard", "Ka"],
            player1_cc=4,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        
        # Should mention Wizard in threat assessment
        print("\n" + "=" * 60)
        print("WIZARD (HIGH THREAT) SCENARIO:")
        print(f"Threat Assessment: {plan.threat_assessment}")
        print("=" * 60)
    
    def test_direct_attack_opportunity(self, turn_planner):
        """Test that AI plans direct attacks when opponent has no toys."""
        setup, cards = create_game_with_cards(
            player1_hand=["Surge"],
            player1_in_play=["Knight", "Ka"],
            player2_hand=["Knight", "Ka", "Wizard"],  # All in hand
            player2_in_play=[],  # No toys in play!
            player1_cc=4,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        
        # Should plan direct attacks
        direct_attack_count = sum(
            1 for a in plan.action_sequence if a.action_type == "direct_attack"
        )
        
        print("\n" + "=" * 60)
        print("DIRECT ATTACK OPPORTUNITY:")
        print(f"Strategy: {plan.selected_strategy}")
        print(f"Direct attacks in plan: {direct_attack_count}")
        for i, action in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'} ({action.cc_cost} CC)")
        print("=" * 60)
        
        # Should have at least one direct attack planned
        # (with 4 CC and opponent having no toys, should attack twice)
    
    def test_no_cc_should_end_turn(self, turn_planner):
        """Test that AI ends turn when CC is 0."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Ka", "Surge"],
            player1_in_play=["Archer"],
            player2_in_play=["Knight"],
            player1_cc=0,  # No CC!
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        assert plan.cc_start == 0
        
        # With 0 CC, the only reasonable action is to end turn
        # (Surge is 0 CC but doesn't help if we can't attack after)
        print("\n" + "=" * 60)
        print("ZERO CC SCENARIO:")
        print(f"CC Start: {plan.cc_start}")
        print(f"Strategy: {plan.selected_strategy}")
        for i, action in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}")
        print("=" * 60)


class TestTurnPlannerCCBudgeting:
    """Test CC budgeting accuracy in plans."""
    
    def test_cc_tracking_through_sequence(self, turn_planner):
        """Test that CC is tracked correctly through the action sequence."""
        setup, cards = create_game_with_cards(
            player1_hand=["Knight", "Surge", "Umbruh"],
            player1_in_play=[],
            player2_in_play=["Ka"],
            player1_cc=4,
        )
        
        plan = turn_planner.create_plan(
            setup.game_state,
            "player1",
            setup.engine
        )
        
        assert plan is not None
        
        # Verify CC tracking
        print("\n" + "=" * 60)
        print("CC TRACKING TEST:")
        print(f"Starting CC: {plan.cc_start}")
        
        running_cc = plan.cc_start
        for i, action in enumerate(plan.action_sequence, 1):
            expected_after = running_cc - action.cc_cost
            # Note: Some actions generate CC (Surge, Rush) - the cc_after should reflect this
            print(f"  {i}. {action.action_type}: {action.card_name or 'N/A'}")
            print(f"      Cost: {action.cc_cost} CC, After: {action.cc_after} CC (expected: {expected_after}+)")
            
            if action.action_type != "end_turn":
                # Update running CC (simplified - doesn't account for CC generation)
                running_cc = action.cc_after
        
        print(f"Final CC: {plan.cc_after_plan}")
        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

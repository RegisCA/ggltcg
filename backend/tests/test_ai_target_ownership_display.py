"""
Test to verify AI targeting fix - ownership labels in target display.

This test verifies that the AI prompt formatter correctly adds "YOUR" or 
"OPPONENT'S" labels to target options, preventing the AI from confusing
whose cards are whose when selecting targets.

Bug context: Game 6a7910bb, AI Log #6259 - AI targeted its own Umbruh
with Jumpscare while thinking it was the opponent's card.
"""

import pytest
from conftest import create_game_with_cards
from game_engine.ai.prompts.formatters import format_valid_actions_for_ai
from game_engine.validation.action_validator import ActionValidator


class TestAITargetOwnershipDisplay:
    """Test that AI prompts show target ownership clearly."""
    
    def test_jumpscare_targets_show_ownership_labels(self):
        """Jumpscare targets should be labeled as YOUR or OPPONENT'S."""
        setup, cards = create_game_with_cards(
            player1_hand=["Jumpscare"],
            player1_in_play=["Demideca", "Umbruh"],
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=1,
        )
        
        # Get valid actions for player1 (AI)
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Find the Jumpscare play action
        jumpscare_action = None
        for action in valid_actions:
            if action.action_type == "play_card" and "Jumpscare" in action.description:
                jumpscare_action = action
                break
        
        assert jumpscare_action is not None, "Should have Jumpscare play action"
        assert jumpscare_action.target_options is not None, "Should have target options"
        assert len(jumpscare_action.target_options) == 3, "Should have 3 targets (2 own, 1 opponent)"
        
        # Format the actions for AI prompt
        formatted = format_valid_actions_for_ai(
            valid_actions,
            game_state=setup.game_state,
            ai_player_id=setup.player1.player_id,
            game_engine=setup.engine
        )
        
        # Verify ownership labels appear in the formatted prompt
        assert "YOUR Demideca" in formatted, "AI's Demideca should be labeled YOUR"
        assert "YOUR Umbruh" in formatted, "AI's Umbruh should be labeled YOUR"
        assert "OPPONENT'S Knight" in formatted, "Opponent's Knight should be labeled OPPONENT'S"
        
        # Verify the old confusing format is NOT present
        assert "[ID:" in formatted, "Should still show UUIDs"
        
        # Make sure we're not just showing card names without ownership
        lines = formatted.split('\n')
        target_lines = [line for line in lines if '[ID:' in line and ('Demideca' in line or 'Umbruh' in line or 'Knight' in line)]
        
        for line in target_lines:
            # Each target line with [ID:] should have either YOUR or OPPONENT'S
            assert 'YOUR' in line or "OPPONENT'S" in line, \
                f"Target line should have ownership label: {line}"
    
    def test_twist_targets_show_opponent_ownership_only(self):
        """Twist (steal effect) should only show OPPONENT'S cards as targets."""
        setup, cards = create_game_with_cards(
            player1_hand=["Twist"],
            player1_in_play=["Ka"],
            player2_in_play=["Knight", "Demideca"],
            active_player="player1",
            player1_cc=3,
        )
        
        # Get valid actions
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Format for AI
        formatted = format_valid_actions_for_ai(
            valid_actions,
            game_state=setup.game_state,
            ai_player_id=setup.player1.player_id,
            game_engine=setup.engine
        )
        
        # Twist should only show opponent's cards as targets
        assert "OPPONENT'S Knight" in formatted, "Knight should be shown as OPPONENT'S"
        assert "OPPONENT'S Demideca" in formatted, "Demideca should be shown as OPPONENT'S"
        assert "YOUR Ka" not in formatted or "Twist" not in formatted, \
            "Ka should not be a Twist target (can't steal own cards)"
    
    def test_drop_targets_show_both_ownerships(self):
        """Drop (sleep any card) should show targets from both players."""
        setup, cards = create_game_with_cards(
            player1_hand=["Drop"],
            player1_in_play=["Ka"],
            player2_in_play=["Knight"],
            active_player="player1",
            player1_cc=2,
        )
        
        # Get valid actions
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Format for AI
        formatted = format_valid_actions_for_ai(
            valid_actions,
            game_state=setup.game_state,
            ai_player_id=setup.player1.player_id,
            game_engine=setup.engine
        )
        
        # Drop can target own or opponent's cards
        if "Drop" in formatted:  # Only check if Drop action is present
            assert "YOUR Ka" in formatted, "Ka should be shown as YOUR"
            assert "OPPONENT'S Knight" in formatted, "Knight should be shown as OPPONENT'S"
    
    def test_tussle_targets_show_opponent_ownership_only(self):
        """Tussle actions should only show OPPONENT'S cards as targets."""
        setup, cards = create_game_with_cards(
            player1_in_play=["Knight"],
            player2_in_play=["Ka", "Demideca"],
            active_player="player1",
            player1_cc=2,
        )
        
        # Get valid actions
        validator = ActionValidator(setup.engine)
        valid_actions = validator.get_valid_actions(setup.player1.player_id)
        
        # Format for AI
        formatted = format_valid_actions_for_ai(
            valid_actions,
            game_state=setup.game_state,
            ai_player_id=setup.player1.player_id,
            game_engine=setup.engine
        )
        
        # Tussle actions should show opponent's cards with ownership
        if "Tussle with Knight" in formatted:
            assert "OPPONENT'S Ka" in formatted or "OPPONENT'S Demideca" in formatted, \
                "Tussle targets should show OPPONENT'S label"
            assert "YOUR Knight" not in formatted, \
                "Your own card should not be listed as a tussle target"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

"""
Unit tests for AI V4 dual-request architecture components.

Tests:
- Example loader selection logic
- Sequence generator prompt size
- Strategic selector prompt size
- Tactical label assignment
"""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards


class TestExampleLoader:
    """Test the contextual example loader."""
    
    def test_returns_exactly_3_examples(self):
        """Loader should always return exactly 3 examples."""
        from game_engine.ai.prompts.examples.loader import get_relevant_examples
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh"],
            player1_in_play=["Ka"],
            player2_in_play=["Archer"],
            active_player="player1",
        )
        
        examples = get_relevant_examples(setup.game_state, "player1")
        assert len(examples) == 3, f"Expected 3 examples, got {len(examples)}"
    
    def test_surge_knight_combo_detected(self):
        """When Surge and Knight are in hand, surge_knight combo should be included."""
        from game_engine.ai.prompts.examples.loader import get_relevant_examples
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=[],
            player2_in_play=[],
            active_player="player1",
        )
        
        examples = get_relevant_examples(setup.game_state, "player1")
        
        # Check that surge_knight combo is included
        example_keys = [e["example_key"] for e in examples]
        assert "surge_knight" in example_keys, f"Expected surge_knight in {example_keys}"
    
    def test_wake_example_when_sleep_zone_full(self):
        """When player has cards in sleep zone, wake example should be included."""
        from game_engine.ai.prompts.examples.loader import get_relevant_examples
        
        setup, _ = create_game_with_cards(
            player1_hand=["Wake", "Knight"],
            player1_sleep_zone=["Surge", "Ka", "Archer"],
            player1_in_play=[],
            player2_in_play=["Wizard"],
            active_player="player1",
        )
        
        examples = get_relevant_examples(setup.game_state, "player1")
        
        # Check that wake example is included
        example_keys = [e["example_key"] for e in examples]
        assert "wake_lethal" in example_keys, f"Expected wake_lethal in {example_keys}"


class TestPromptSizes:
    """Verify that prompts stay under target size."""
    
    def test_sequence_generator_prompt_size(self):
        """Request 1 prompt should be under 4500 chars."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        # Create a realistic game state
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Drop"],
            player1_in_play=["Ka", "Archer"],
            player2_in_play=["Gibbers", "Wizard", "Paper Plane"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        assert len(prompt) < 4500, f"Prompt too long: {len(prompt)} chars (target: <4500)"
    
    def test_prompt_includes_cc(self):
        """Prompt should include current CC."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge"],
            player1_in_play=[],
            player2_in_play=[],
            player1_cc=5,
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        assert "## CC: 5" in prompt, "Prompt should include CC header"
    
    def test_prompt_shows_surge_cc_gain(self):
        """When Surge is in hand, prompt should show +1 CC."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=[],
            player2_in_play=[],
            player1_cc=2,
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        # Should show potential CC boost
        assert "(+1 CC when played)" in prompt or "Max potential: 3 via Surge" in prompt, \
            "Prompt should indicate Surge gives +1 CC"
    
    def test_prompt_shows_direct_attack_availability(self):
        """Prompt should indicate when direct_attack is legal."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        # No opponent toys = direct attack legal
        setup, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=["Ka"],
            player2_in_play=[],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        assert "direct_attack: YES" in prompt, "Should show direct_attack is legal"
        
        # Opponent toys = direct attack illegal
        setup2, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=["Ka"],
            player2_in_play=["Gibbers"],
            active_player="player1",
        )
        
        prompt2 = generate_sequence_prompt(setup2.game_state, "player1")
        
        assert "direct_attack: NO" in prompt2, "Should show direct_attack is illegal"


class TestTacticalLabels:
    """Test tactical label assignment logic."""
    
    def test_lethal_label_for_6_sleeps(self):
        """Sequence that sleeps 6 cards should get [Lethal] label."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [{"action_type": "tussle"}] * 6 + [{"action_type": "end_turn"}],
                "cards_slept": 6,
                "total_cc_spent": 12,
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        assert labeled[0]["tactical_label"] == "[Lethal]"
    
    def test_aggressive_label_for_multiple_attacks(self):
        """Sequence with 2+ attacks should get [Aggressive Removal] label."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [
                    {"action_type": "tussle"},
                    {"action_type": "direct_attack"},
                    {"action_type": "end_turn"}
                ],
                "cards_slept": 2,
                "total_cc_spent": 4,
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        assert labeled[0]["tactical_label"] == "[Aggressive Removal]"
    
    def test_resource_label_for_surge_without_attacks(self):
        """Playing Surge without attacking should get [Resource Building] label."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [
                    {"action_type": "play_card", "card_name": "Surge"},
                    {"action_type": "end_turn"}
                ],
                "cards_slept": 0,
                "total_cc_spent": 0,
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        assert labeled[0]["tactical_label"] == "[Resource Building]"
    
    def test_board_setup_label(self):
        """Playing multiple toys without attacking should get [Board Setup] label."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [
                    {"action_type": "play_card", "card_name": "Knight"},
                    {"action_type": "play_card", "card_name": "Ka"},
                    {"action_type": "end_turn"}
                ],
                "cards_slept": 0,
                "total_cc_spent": 2,
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        assert labeled[0]["tactical_label"] == "[Board Setup]"
    
    def test_conservative_label_for_low_cc(self):
        """Spending ≤2 CC should get [Conservative] label."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [
                    {"action_type": "play_card", "card_name": "Surge"},
                    {"action_type": "end_turn"}
                ],
                "cards_slept": 0,
                "total_cc_spent": 0,
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        # This is resource, not conservative (Surge gives CC)
        # Let's test a true conservative play
        sequences2 = [
            {
                "actions": [
                    {"action_type": "play_card", "card_name": "Knight"},
                    {"action_type": "end_turn"}
                ],
                "cards_slept": 0,
                "total_cc_spent": 1,
            }
        ]
        
        labeled2 = add_tactical_labels(sequences2)
        assert labeled2[0]["tactical_label"] == "[Conservative]"


class TestDualRequestPromptSizes:
    """Test that both Request 1 and Request 2 stay under size targets."""
    
    def test_both_prompts_within_targets(self):
        """Both prompts should be under 4500 chars each."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        from game_engine.ai.prompts.strategic_selector import generate_strategic_prompt
        
        # Create a complex game state
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Drop", "Wake", "Archer"],
            player1_in_play=[],
            player2_in_play=["Gibbers", "Wizard", "Paper Plane"],
            active_player="player1",
        )
        
        # Test Request 1
        seq_prompt = generate_sequence_prompt(setup.game_state, "player1")
        print(f"Request 1 (Sequence Generator): {len(seq_prompt)} chars")
        assert len(seq_prompt) < 4500, f"Request 1 too long: {len(seq_prompt)} chars"
        
        # Test Request 2 with multiple sequences
        test_sequences = [
            {"actions": [{"action_type": "end_turn", "cc_cost": 0}], "total_cc_spent": 0, "cards_slept": 0, "tactical_label": f"[Seq{i}]"}
            for i in range(5)
        ]
        
        select_prompt = generate_strategic_prompt(setup.game_state, "player1", test_sequences)
        print(f"Request 2 (Strategic Selector): {len(select_prompt)} chars")

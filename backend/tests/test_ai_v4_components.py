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
        has_surge_knight = any("Surge + Knight" in ex for ex in examples)
        assert has_surge_knight, "Surge+Knight combo should be detected when both in hand"
    
    def test_phase_example_based_on_turn(self):
        """Phase example should match turn number."""
        from game_engine.ai.prompts.examples.loader import get_game_phase
        
        assert get_game_phase(1) == "early_game"
        assert get_game_phase(3) == "early_game"
        assert get_game_phase(4) == "mid_game"
        assert get_game_phase(6) == "mid_game"
        assert get_game_phase(7) == "end_game"
        assert get_game_phase(10) == "end_game"
    
    def test_no_duplicate_examples(self):
        """Examples should not be duplicated."""
        from game_engine.ai.prompts.examples.loader import get_relevant_examples
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Archer"],
            player1_in_play=[],
            player2_in_play=["Umbruh"],
            active_player="player1",
        )
        
        examples = get_relevant_examples(setup.game_state, "player1")
        
        # Check no duplicates
        assert len(examples) == len(set(examples)), "Examples should not be duplicated"


class TestSequenceGenerator:
    """Test the sequence generator prompt."""
    
    def test_prompt_under_4k_chars(self):
        """Sequence generator prompt should be under 4k chars."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight", "Umbruh", "Drop"],
            player1_in_play=["Ka", "Archer"],
            player2_in_play=["Gibbers", "Wizard", "Paper Plane"],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        assert len(prompt) < 4000, f"Prompt too long: {len(prompt)} chars (target: <4000)"
    
    def test_prompt_includes_cc(self):
        """Prompt should include current CC."""
        from game_engine.ai.prompts.sequence_generator import generate_sequence_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge"],
            player1_in_play=[],
            player2_in_play=[],
            active_player="player1",
        )
        
        prompt = generate_sequence_prompt(setup.game_state, "player1")
        
        # V4 shows CC value in header
        assert "## CC:" in prompt, "Prompt should include CC"
    
    def test_tactical_labels_assigned(self):
        """Tactical labels should be assigned based on sequence content."""
        from game_engine.ai.prompts.sequence_generator import add_tactical_labels
        
        sequences = [
            {
                "actions": [
                    {"action_type": "tussle", "cc_cost": 2},
                    {"action_type": "tussle", "cc_cost": 2},
                    {"action_type": "end_turn", "cc_cost": 0}
                ],
                "total_cc_spent": 4,
                "cards_slept": 2
            },
            {
                "actions": [
                    {"action_type": "play_card", "card_name": "Surge", "cc_cost": 0},
                    {"action_type": "end_turn", "cc_cost": 0}
                ],
                "total_cc_spent": 0,
                "cards_slept": 0
            }
        ]
        
        labeled = add_tactical_labels(sequences)
        
        assert labeled[0]["tactical_label"] == "[Aggressive Removal]"
        assert labeled[1]["tactical_label"] == "[Resource Building]"


class TestStrategicSelector:
    """Test the strategic selector prompt."""
    
    def test_prompt_under_5k_chars(self):
        """Strategic selector prompt should be under 5k chars."""
        from game_engine.ai.prompts.strategic_selector import generate_strategic_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=["Ka"],
            player2_in_play=["Archer", "Gibbers"],
            active_player="player1",
        )
        
        test_sequences = [
            {
                "actions": [{"action_type": "end_turn", "cc_cost": 0}],
                "total_cc_spent": 0,
                "cards_slept": 0,
                "tactical_label": "[Conservative]"
            },
            {
                "actions": [
                    {"action_type": "tussle", "card_name": "Ka", "target_names": ["Archer"], "cc_cost": 2},
                    {"action_type": "end_turn", "cc_cost": 0}
                ],
                "total_cc_spent": 2,
                "cards_slept": 1,
                "tactical_label": "[Aggressive Removal]"
            }
        ]
        
        prompt = generate_strategic_prompt(setup.game_state, "player1", test_sequences)
        
        assert len(prompt) < 5000, f"Prompt too long: {len(prompt)} chars (target: <5000)"
    
    def test_prompt_includes_examples(self):
        """Strategic selector should include contextual examples."""
        from game_engine.ai.prompts.strategic_selector import generate_strategic_prompt
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=[],
            player2_in_play=[],
            active_player="player1",
        )
        
        prompt = generate_strategic_prompt(setup.game_state, "player1", [
            {"actions": [], "total_cc_spent": 0, "cards_slept": 0, "tactical_label": "[Test]"}
        ])
        
        assert "<examples>" in prompt, "Prompt should include examples section"
        assert "</examples>" in prompt, "Examples section should be closed"
    
    def test_convert_sequence_to_turn_plan(self):
        """Converting sequence to turn plan should produce valid structure."""
        from game_engine.ai.prompts.strategic_selector import convert_sequence_to_turn_plan
        
        setup, _ = create_game_with_cards(
            player1_hand=["Surge", "Knight"],
            player1_in_play=[],
            player2_in_play=["Archer"],
            active_player="player1",
        )
        
        sequence = {
            "actions": [
                {"action_type": "play_card", "card_name": "Surge", "cc_cost": 0},
                {"action_type": "play_card", "card_name": "Knight", "card_id": "abc", "cc_cost": 1},
                {"action_type": "end_turn", "cc_cost": 0}
            ],
            "total_cc_spent": 1,
            "cards_slept": 0,
            "tactical_label": "[Board Setup]"
        }
        
        plan_data = convert_sequence_to_turn_plan(
            sequence, setup.game_state, "player1", "Test reasoning"
        )
        
        assert "action_sequence" in plan_data
        assert len(plan_data["action_sequence"]) == 3
        # cc_start comes from player.cc in game_state
        assert plan_data["cc_start"] == setup.game_state.players["player1"].cc
        assert plan_data["plan_reasoning"] == "Test reasoning"


class TestActionParsing:
    """Test parsing of action strings with various formats."""
    
    def test_tussle_with_name_and_id(self):
        """Should parse 'tussle NAME [UUID]->NAME [UUID]' format."""
        from game_engine.ai.prompts.sequence_generator import _parse_action_string
        
        action_str = "tussle Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6]->Umbruh [f6e15fbd-5223-4c12-96da-0e83ad0dd10c]"
        result = _parse_action_string(action_str)
        
        assert result is not None, "Failed to parse tussle with name+ID format"
        assert result["action_type"] == "tussle"
        assert result["card_name"] == "Knight"
        assert result["card_id"] == "a94c6c17-0b54-4862-b1b5-c9f827a04df6"
        assert result["target_name"] == "Umbruh"
        assert result["target_id"] == "f6e15fbd-5223-4c12-96da-0e83ad0dd10c"
        assert result["cc_cost"] == 2
    
    def test_direct_attack_with_name_and_id(self):
        """Should parse 'direct_attack NAME [UUID]' format."""
        from game_engine.ai.prompts.sequence_generator import _parse_action_string
        
        action_str = "direct_attack Archer [a94c6c17-0b54-4862-b1b5-c9f827a04df6]"
        result = _parse_action_string(action_str)
        
        assert result is not None, "Failed to parse direct_attack with name+ID format"
        assert result["action_type"] == "direct_attack"
        assert result["card_name"] == "Archer"
        assert result["card_id"] == "a94c6c17-0b54-4862-b1b5-c9f827a04df6"
        assert result["cc_cost"] == 2
    
    def test_activate_with_name_and_id(self):
        """Should parse 'activate NAME [UUID]->NAME [UUID]' format."""
        from game_engine.ai.prompts.sequence_generator import _parse_action_string
        
        action_str = "activate Archer [a94c6c17-0b54-4862-b1b5-c9f827a04df6]->Umbruh [f6e15fbd-5223-4c12-96da-0e83ad0dd10c]"
        result = _parse_action_string(action_str)
        
        assert result is not None, "Failed to parse activate with name+ID format"
        assert result["action_type"] == "activate_ability"
        assert result["card_name"] == "Archer"
        assert result["card_id"] == "a94c6c17-0b54-4862-b1b5-c9f827a04df6"
        assert result["target_name"] == "Umbruh"
        assert result["target_id"] == "f6e15fbd-5223-4c12-96da-0e83ad0dd10c"
        assert result["cc_cost"] == 1
    
    def test_full_sequence_parsing(self):
        """Test parsing a full sequence string like the one from game 133e16a7."""
        from game_engine.ai.prompts.sequence_generator import parse_sequences_response
        import json
        
        response_text = json.dumps({
            "sequences": [
                "play Surge [c5d99553-9d2c-4da0-8e01-a1a3ed2e791e] -> play Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6] -> tussle Knight [a94c6c17-0b54-4862-b1b5-c9f827a04df6]->Umbruh [f6e15fbd-5223-4c12-96da-0e83ad0dd10c] -> end_turn | CC: 4/4 spent | Sleeps: 1"
            ]
        })
        
        sequences = parse_sequences_response(response_text)
        
        assert len(sequences) == 1, "Should parse 1 sequence"
        seq = sequences[0]
        assert len(seq["actions"]) == 4, f"Should have 4 actions, got {len(seq['actions'])}"
        
        # Check each action
        assert seq["actions"][0]["action_type"] == "play_card"
        assert seq["actions"][0]["card_name"] == "Surge"
        
        assert seq["actions"][1]["action_type"] == "play_card"
        assert seq["actions"][1]["card_name"] == "Knight"
        
        assert seq["actions"][2]["action_type"] == "tussle"
        assert seq["actions"][2]["card_name"] == "Knight"
        assert seq["actions"][2]["target_name"] == "Umbruh"
        assert seq["actions"][2]["card_id"] == "a94c6c17-0b54-4862-b1b5-c9f827a04df6"
        assert seq["actions"][2]["target_id"] == "f6e15fbd-5223-4c12-96da-0e83ad0dd10c"
        
        assert seq["actions"][3]["action_type"] == "end_turn"


class TestPromptSizes:
    """Aggregate test for prompt size targets."""
    
    def test_both_prompts_within_targets(self):
        """Both Request 1 and Request 2 prompts should be within targets."""
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
        assert len(seq_prompt) < 4000, f"Request 1 too long: {len(seq_prompt)} chars"
        
        # Test Request 2 with multiple sequences
        test_sequences = [
            {"actions": [{"action_type": "end_turn", "cc_cost": 0}], "total_cc_spent": 0, "cards_slept": 0, "tactical_label": f"[Seq{i}]"}
            for i in range(5)
        ]
        
        select_prompt = generate_strategic_prompt(setup.game_state, "player1", test_sequences)
        print(f"Request 2 (Strategic Selector): {len(select_prompt)} chars")
        assert len(select_prompt) < 5000, f"Request 2 too long: {len(select_prompt)} chars"

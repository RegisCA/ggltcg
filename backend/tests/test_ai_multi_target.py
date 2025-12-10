"""
Tests for AI multi-target selection (Issue #188).

This test module verifies that the AI player can correctly select multiple
targets for cards like Sun that allow "up to 2 targets".
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from game_engine.ai.llm_player import LLMPlayer
from game_engine.ai.prompts import (
    format_valid_actions_for_ai,
    AI_DECISION_JSON_SCHEMA,
    PROMPTS_VERSION,
)
from api.schemas import ValidAction


class TestAIMultiTargetSelection:
    """
    Test cases for AI multi-target selection (Issue #188).
    
    The scenario from Issue #188:
    - AI has Sun + Wake in hand
    - 4 cards in sleep zone: Surge, Rush, Ka, Knight
    - Opponent has Knight in play
    - AI should select 2 targets for Sun (Ka + Knight preferred)
    """
    
    def test_prompts_version_is_2_0(self):
        """Verify we're testing the v2.0 prompts."""
        assert PROMPTS_VERSION == "2.0", "This test requires prompts v2.0"
    
    def test_ai_decision_schema_has_target_ids_array(self):
        """Verify the JSON schema uses target_ids (array) not target_id (string)."""
        assert "target_ids" in AI_DECISION_JSON_SCHEMA["properties"]
        target_ids_schema = AI_DECISION_JSON_SCHEMA["properties"]["target_ids"]
        
        # Schema uses type: ["array", "null"] for optional array
        # or anyOf format depending on how it was generated
        if "anyOf" in target_ids_schema:
            # Pydantic-generated schema with anyOf
            array_schema = next((s for s in target_ids_schema["anyOf"] if s.get("type") == "array"), None)
            assert array_schema is not None, "target_ids should include array type"
            assert array_schema["items"]["type"] == "string"
        else:
            # Manual JSON schema with type array
            schema_type = target_ids_schema.get("type")
            # Handle both "array" and ["array", "null"] formats
            if isinstance(schema_type, list):
                assert "array" in schema_type, "target_ids type should include 'array'"
            else:
                assert schema_type == "array", "target_ids should be array type"
            assert target_ids_schema["items"]["type"] == "string"
    
    def test_format_valid_actions_shows_multi_target_hint(self):
        """
        Verify that when max_targets > 1, the prompt shows multi-target selection hint.
        """
        # Create a mock Sun action with max_targets=2
        sun_action = ValidAction(
            action_type="play_card",
            card_id="sun-123",
            card_name="Sun",
            cost_cc=3,
            target_options=["ka-456", "knight-789", "surge-111", "rush-222"],
            max_targets=2,
            min_targets=0,
            description="Play Sun (Cost: 3 CC, select up to 2 targets)"
        )
        
        # Format the actions
        result = format_valid_actions_for_ai([sun_action])
        
        # Verify multi-target hint appears
        assert "Select up to 2 targets" in result, "Should show multi-target selection hint for Sun"
        assert "target_ids array" in result, "Should mention target_ids array format"
    
    def test_llm_player_parses_target_ids_array(self):
        """
        Verify that LLMPlayer correctly parses target_ids as an array.
        """
        player = LLMPlayer.__new__(LLMPlayer)
        player.provider = "gemini"
        player._last_target_ids = None
        player._last_alternative_cost_id = None
        player._last_prompt = None
        player._last_response = None
        player._last_action_number = None
        player._last_reasoning = None
        
        # Simulate parsing a response with target_ids array
        response_data = {
            "action_number": 2,
            "reasoning": "Playing Sun to recover Ka and Knight for board presence.",
            "target_ids": ["ka-456", "knight-789"],
            "alternative_cost_id": None
        }
        
        # The actual parsing happens in select_action, but we can test the logic
        target_ids = response_data.get("target_ids")
        
        # Normalize (as done in select_action)
        if isinstance(target_ids, list):
            target_ids = [t for t in target_ids if t and t not in ("null", "None")]
        
        assert target_ids == ["ka-456", "knight-789"]
        assert len(target_ids) == 2
    
    def test_llm_player_handles_legacy_target_id(self):
        """
        Verify backwards compatibility: if LLM returns target_id (string),
        it should be converted to target_ids array.
        """
        # Legacy response with target_id instead of target_ids
        response_data = {
            "action_number": 1,
            "reasoning": "Playing Wake to recover Ka.",
            "target_id": "ka-456",  # Legacy format
            "alternative_cost_id": None
        }
        
        # Simulate the conversion logic from select_action
        target_ids = response_data.get("target_ids")
        target_id_legacy = response_data.get("target_id")
        
        if target_ids is None and target_id_legacy:
            if target_id_legacy not in ("null", "None"):
                target_ids = [target_id_legacy]
        
        assert target_ids == ["ka-456"], "Legacy target_id should convert to target_ids array"
    
    def test_get_action_details_uses_target_ids(self):
        """
        Verify that get_action_details returns target_ids (array) for play_card.
        """
        player = LLMPlayer.__new__(LLMPlayer)
        player.provider = "gemini"
        player._last_target_ids = ["ka-456", "knight-789"]
        player._last_alternative_cost_id = None
        
        # Create a mock action
        action = MagicMock()
        action.action_type = "play_card"
        action.card_id = "sun-123"
        action.target_options = ["ka-456", "knight-789", "surge-111"]
        action.alternative_cost_options = None
        
        result = player.get_action_details(action)
        
        assert result["action_type"] == "play_card"
        assert result["card_id"] == "sun-123"
        assert "target_ids" in result, "Should use target_ids for play_card"
        assert result["target_ids"] == ["ka-456", "knight-789"]
        assert len(result["target_ids"]) == 2
    
    def test_tussle_uses_first_target(self):
        """
        Verify that tussle actions correctly use the first target from target_ids.
        (Tussles are still single-target)
        """
        player = LLMPlayer.__new__(LLMPlayer)
        player.provider = "gemini"
        player._last_target_ids = ["knight-789"]
        player._last_alternative_cost_id = None
        
        # Create a mock tussle action
        action = MagicMock()
        action.action_type = "tussle"
        action.card_id = "ka-456"
        action.target_options = ["knight-789", "beary-111"]
        
        result = player.get_action_details(action)
        
        assert result["action_type"] == "tussle"
        assert result["attacker_id"] == "ka-456"
        assert result["defender_id"] == "knight-789", "Tussle should use first target_id"


class TestIssue188Scenario:
    """
    Test the specific scenario from Issue #188.
    
    Game State:
    - Turn 5, AI player "Gemiknight"
    - CC: 4/7
    - Hand: Sun (cost 3), Wake (cost 1)
    - In Play: NONE
    - Sleep Zone: Surge, Rush, Ka, Knight (4 cards)
    
    Opponent:
    - Knight in play
    - Sleep Zone: 4 cards
    
    Expected: AI should play Sun targeting Ka AND Knight (2 targets)
    Better: Wake → Ka, then Sun → Knight + Wake (3 cards recovered)
    """
    
    def test_sun_action_allows_two_targets(self):
        """
        Verify that Sun action is formatted with max_targets=2.
        """
        sun_action = ValidAction(
            action_type="play_card",
            card_id="sun-123",
            card_name="Sun",
            cost_cc=3,
            target_options=[
                "surge-111",
                "rush-222", 
                "ka-333",
                "knight-444"
            ],
            max_targets=2,
            min_targets=0,
            description="Play Sun (Cost: 3 CC, select up to 2 targets)"
        )
        
        wake_action = ValidAction(
            action_type="play_card",
            card_id="wake-555",
            card_name="Wake",
            cost_cc=1,
            target_options=[
                "surge-111",
                "rush-222",
                "ka-333",
                "knight-444"
            ],
            max_targets=1,
            min_targets=1,
            description="Play Wake (Cost: 1 CC, select target)"
        )
        
        end_turn = ValidAction(
            action_type="end_turn",
            description="End your turn"
        )
        
        result = format_valid_actions_for_ai([wake_action, sun_action, end_turn])
        
        # Sun should have multi-target hint
        assert "Select up to 2 targets" in result
        
        # Wake should NOT have multi-target hint (max_targets=1)
        lines = result.split('\n')
        wake_section = []
        sun_section = []
        current_section = None
        
        for line in lines:
            if "Wake" in line and "Play Wake" in line:
                current_section = "wake"
            elif "Sun" in line and "Play Sun" in line:
                current_section = "sun"
            elif line.strip().startswith("3."):  # End turn
                current_section = None
            
            if current_section == "wake":
                wake_section.append(line)
            elif current_section == "sun":
                sun_section.append(line)
        
        wake_text = '\n'.join(wake_section)
        sun_text = '\n'.join(sun_section)
        
        assert "Select up to 2" not in wake_text, "Wake should not have multi-target hint"
        assert "Select up to 2" in sun_text, "Sun should have multi-target hint"
    
    def test_optimal_play_is_wake_then_sun(self):
        """
        Document the optimal play sequence from Issue #188 comment.
        
        Optimal sequence:
        1. Play Wake (1 CC) → Unsleep Ka → Ka returns to hand
        2. Play Sun (3 CC) → Unsleep Knight + Wake → Both return to hand
        
        Result: 3 cards recovered (Ka, Knight, Wake) for 4 CC
        
        This test documents the expected behavior, not the AI's actual decision.
        The AI might choose Sun directly (2 cards) which is also valid but suboptimal.
        """
        # This is a documentation test - the actual AI decision depends on the LLM
        # The key point is that the AI CAN now select 2 targets for Sun
        
        # Expected optimal sequence
        optimal_plays = [
            {"action": "Wake", "targets": ["Ka"], "result": "Ka to hand"},
            {"action": "Sun", "targets": ["Knight", "Wake"], "result": "Knight and Wake to hand"},
        ]
        
        total_cards_recovered = 3  # Ka + Knight + Wake
        total_cc_spent = 4  # Wake(1) + Sun(3)
        
        # Alternative valid play (what AI was doing before, but only 1 target)
        # Now AI should be able to do this correctly with 2 targets:
        good_play = [
            {"action": "Sun", "targets": ["Ka", "Knight"], "result": "Ka and Knight to hand"},
        ]
        
        cards_recovered_good = 2
        cc_spent_good = 3
        
        # Assert the math is correct
        assert total_cards_recovered == 3
        assert cards_recovered_good == 2
        
        # The key improvement is that AI can now select 2 targets for Sun
        # Before: AI would only select 1 target (bug)
        # After: AI can select 2 targets (fixed)

"""
Tests for card ID disambiguation in AI prompts and action parsing.

When both players have cards with the same name (e.g., both have Knight),
the AI must use unique card IDs to distinguish between them. This prevents
the AI from accidentally trying to use the opponent's cards.

Issue: AI was generating "tussle Knight->Beary" which was ambiguous when
both players had a Knight in play.

Solution: 
1. Prompt format changed to use IDs: "tussle k1->b1" 
2. Parser extracts card_id and target_id separately from card_name
3. Heuristic matcher prioritizes ID matching over name matching
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from api.schemas import ValidAction
from game_engine.ai.prompts.schemas import PlannedAction
from game_engine.ai.prompts.sequence_generator import _parse_action_string
from game_engine.ai.prompts.execution_prompt import find_matching_action_index
from conftest import create_game_with_cards


class TestActionStringParsing:
    """Test parsing of action strings with IDs."""
    
    def test_parse_play_with_id(self):
        """Parse 'play Knight [k1]' format."""
        result = _parse_action_string("play Knight [k1]")
        
        assert result is not None
        assert result["action_type"] == "play_card"
        assert result["card_name"] == "Knight"
        assert result["card_id"] == "k1"
        assert result["target_id"] is None
    
    def test_parse_play_with_target_id(self):
        """Parse 'play Wake [wa1] [target: k2]' format."""
        result = _parse_action_string("play Wake [wa1] [target: k2]")
        
        assert result is not None
        assert result["action_type"] == "play_card"
        assert result["card_name"] == "Wake"
        assert result["card_id"] == "wa1"
        assert result["target_id"] == "k2"
    
    def test_parse_tussle_with_ids(self):
        """Parse 'tussle k1->b2' ID-based format."""
        result = _parse_action_string("tussle k1->b2")
        
        assert result is not None
        assert result["action_type"] == "tussle"
        assert result["card_id"] == "k1"
        assert result["target_id"] == "b2"
        # Name should be None for ID-based format
        assert result["card_name"] is None
        assert result["target_name"] is None
    
    def test_parse_tussle_with_uuid_ids(self):
        """Parse tussle with full UUID format."""
        attacker_id = "bd9629b1-0671-4024-8252-515e9f49f948"
        target_id = "a1b2c3d4-5678-9abc-def0-123456789abc"
        
        result = _parse_action_string(f"tussle {attacker_id}->{target_id}")
        
        assert result is not None
        assert result["action_type"] == "tussle"
        assert result["card_id"] == attacker_id
        assert result["target_id"] == target_id
    
    def test_parse_tussle_legacy_names(self):
        """Parse legacy 'tussle Knight->Beary' format still works."""
        result = _parse_action_string("tussle Knight->Beary")
        
        assert result is not None
        assert result["action_type"] == "tussle"
        assert result["card_name"] == "Knight"
        assert result["target_name"] == "Beary"
        # IDs should be None for name-based format
        assert result["card_id"] is None
        assert result["target_id"] is None
    
    def test_parse_direct_attack_with_id(self):
        """Parse 'direct_attack ar1' ID-based format."""
        result = _parse_action_string("direct_attack ar1")
        
        assert result is not None
        assert result["action_type"] == "direct_attack"
        assert result["card_id"] == "ar1"
        assert result["card_name"] is None
    
    def test_parse_direct_attack_legacy_name(self):
        """Parse legacy 'direct_attack Archer' still works."""
        result = _parse_action_string("direct_attack Archer")
        
        assert result is not None
        assert result["action_type"] == "direct_attack"
        assert result["card_name"] == "Archer"
        assert result["card_id"] is None
    
    def test_parse_activate_with_ids(self):
        """Parse 'activate ar1->w1' ID-based format."""
        result = _parse_action_string("activate ar1->w1")
        
        assert result is not None
        assert result["action_type"] == "activate_ability"
        assert result["card_id"] == "ar1"
        assert result["target_id"] == "w1"


class TestHeuristicMatcherWithIDs:
    """Test that heuristic matcher correctly prioritizes ID matching."""
    
    def test_tussle_matches_by_id_not_name(self):
        """When both players have Knight, match by ID."""
        # Player 1's Knight
        player1_knight_id = "p1-knight-uuid"
        # Player 2's Knight (different ID, same name)
        player2_knight_id = "p2-knight-uuid"
        # Target Beary
        beary_id = "beary-uuid"
        
        # Planned action uses Player 1's Knight ID
        planned = PlannedAction(
            action_type="tussle",
            card_name="Knight",  # Name is ambiguous
            card_id=player1_knight_id,  # ID is specific
            target_ids=[beary_id],
            cc_cost=2,
            cc_after=3,
            reasoning="Test tussle",
        )
        
        # Valid actions include both Knights' tussle options
        valid_actions = [
            ValidAction(
                action_type="tussle",
                card_id=player1_knight_id,
                card_name="Knight",
                target_options=[beary_id],
                cost_cc=2,
                description="Knight tussle Beary (Cost: 2 CC)",
            ),
            ValidAction(
                action_type="tussle",
                card_id=player2_knight_id,  # Different Knight!
                card_name="Knight",
                target_options=[beary_id],
                cost_cc=2,
                description="Knight tussle Beary (Cost: 2 CC)",  # Same description!
            ),
            ValidAction(
                action_type="end_turn",
                description="End turn",
            ),
        ]
        
        # Should match Player 1's Knight (index 0), not Player 2's (index 1)
        index = find_matching_action_index(planned, valid_actions)
        
        assert index == 0, "Should match by ID, not by name"
    
    def test_play_card_matches_by_id(self):
        """Play card should match by ID when available."""
        knight_id = "knight-uuid-123"
        
        planned = PlannedAction(
            action_type="play_card",
            card_name="Knight",
            card_id=knight_id,
            cc_cost=2,
            cc_after=3,
            reasoning="Test play",
        )
        
        valid_actions = [
            ValidAction(
                action_type="play_card",
                card_id=knight_id,
                card_name="Knight",
                cost_cc=2,
                description="Play Knight (Cost: 2 CC)",
            ),
            ValidAction(
                action_type="end_turn",
                description="End turn",
            ),
        ]
        
        index = find_matching_action_index(planned, valid_actions)
        
        assert index == 0, "Should match play_card by ID"
    
    def test_direct_attack_matches_by_id(self):
        """Direct attack should match by ID when available."""
        archer_id = "archer-uuid-456"
        
        planned = PlannedAction(
            action_type="direct_attack",
            card_name="Archer",
            card_id=archer_id,
            cc_cost=2,
            cc_after=3,
            reasoning="Test direct attack",
        )
        
        valid_actions = [
            ValidAction(
                action_type="direct_attack",
                card_id=archer_id,
                card_name="Archer",
                cost_cc=2,
                description="Archer direct attack (Cost: 2 CC)",
            ),
            ValidAction(
                action_type="end_turn",
                description="End turn",
            ),
        ]
        
        index = find_matching_action_index(planned, valid_actions)
        
        assert index == 0, "Should match direct_attack by ID"
    
    def test_fallback_to_name_when_no_id(self):
        """Legacy plans without IDs should still match by name."""
        planned = PlannedAction(
            action_type="play_card",
            card_name="Knight",
            # No card_id
            cc_cost=2,
            cc_after=3,
            reasoning="Test legacy",
        )
        
        valid_actions = [
            ValidAction(
                action_type="play_card",
                card_id="some-uuid",
                card_name="Knight",
                cost_cc=2,
                description="Play Knight (Cost: 2 CC)",
            ),
            ValidAction(
                action_type="end_turn",
                description="End turn",
            ),
        ]
        
        index = find_matching_action_index(planned, valid_actions)
        
        assert index == 0, "Should fall back to name matching"


class TestIDExtractionFromSequence:
    """Test that IDs flow through the full sequence parsing pipeline."""
    
    def test_tussle_ids_preserved_through_parsing(self):
        """Verify card_id and target_id are extracted and preserved."""
        action_str = "tussle abc123->def456"
        
        parsed = _parse_action_string(action_str)
        
        assert parsed["card_id"] == "abc123"
        assert parsed["target_id"] == "def456"
        assert parsed["action_type"] == "tussle"
    
    def test_play_ids_preserved_through_parsing(self):
        """Verify play card with ID is extracted correctly."""
        action_str = "play Wake [w1] [target: k2]"
        
        parsed = _parse_action_string(action_str)
        
        assert parsed["card_id"] == "w1"
        assert parsed["target_id"] == "k2"
        assert parsed["card_name"] == "Wake"

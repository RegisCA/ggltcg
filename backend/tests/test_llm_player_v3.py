"""
Integration tests for LLMPlayerV3 two-phase turn planning.

Tests the full flow: plan creation -> action execution -> action matching.
"""

import pytest
from unittest.mock import Mock, patch

from game_engine.ai.llm_player import LLMPlayer, LLMPlayerV3, get_ai_player_v3
from game_engine.ai.prompts.schemas import TurnPlan, PlannedAction
from game_engine.models.game_state import GameState
from api.schemas import ValidAction


# Helper to create mock GameState
def create_mock_game_state(
    ai_cc: int = 4,
    ai_cards_in_hand: list = None,
    ai_field: list = None,
    opp_field: list = None,
    turn_number: int = 3
) -> GameState:
    """Create a mock game state for testing."""
    state = Mock(spec=GameState)
    state.turn_number = turn_number
    
    # AI player
    ai_player = Mock()
    ai_player.cc = ai_cc
    ai_player.id = "ai_player"
    ai_player.hand = ai_cards_in_hand or []
    ai_player.field = ai_field or []
    
    # Opponent
    opp_player = Mock()
    opp_player.cc = 4
    opp_player.id = "opponent"
    opp_player.field = opp_field or []
    
    state.players = {
        "ai_player": ai_player,
        "opponent": opp_player
    }
    state.opponent_id = Mock(return_value="opponent")
    
    return state


def create_mock_valid_actions(action_specs: list) -> list:
    """Create mock ValidAction objects from specs.
    
    Args:
        action_specs: List of tuples (action_type, card_name, description)
    """
    actions = []
    for i, (action_type, card_name, description) in enumerate(action_specs):
        action = Mock(spec=ValidAction)
        action.action_type = action_type
        action.card_name = card_name
        action.description = description
        action.targets = []
        action.target_options = []
        actions.append(action)
    return actions


class TestLLMPlayerV3Initialization:
    """Test v3 player initialization."""
    
    def test_v3_player_inherits_from_llm_player(self):
        """V3 player should inherit from LLMPlayer."""
        assert issubclass(LLMPlayerV3, LLMPlayer)


class TestPlanManagement:
    """Test plan state management."""
    
    @pytest.fixture
    def v3_player(self):
        """Create a V3 player with mocked API."""
        with patch.object(LLMPlayerV3, '__init__', lambda self, **kwargs: None):
            player = LLMPlayerV3.__new__(LLMPlayerV3)
            player._current_plan = None
            player._plan_action_index = 0
            player._completed_actions = []
            player._plan_turn_number = None
            return player
    
    def test_needs_new_plan_when_no_plan(self, v3_player):
        """Should need new plan when _current_plan is None."""
        v3_player._current_plan = None
        
        mock_state = create_mock_game_state()
        assert v3_player._needs_new_plan(mock_state) is True
    
    def test_needs_new_plan_when_plan_exhausted(self, v3_player):
        """Should need new plan when all actions executed."""
        mock_plan = Mock(spec=TurnPlan)
        mock_plan.action_sequence = [Mock(), Mock()]
        
        v3_player._current_plan = mock_plan
        v3_player._plan_action_index = 2  # Past last action
        v3_player._plan_turn_number = 3
        
        mock_state = create_mock_game_state(turn_number=3)
        assert v3_player._needs_new_plan(mock_state) is True
    
    def test_does_not_need_new_plan_mid_execution(self, v3_player):
        """Should not need new plan when actions remain."""
        mock_plan = Mock(spec=TurnPlan)
        mock_plan.action_sequence = [Mock(), Mock(), Mock()]
        
        v3_player._current_plan = mock_plan
        v3_player._plan_action_index = 1  # Still have actions
        v3_player._plan_turn_number = 3
        
        mock_state = create_mock_game_state(turn_number=3)
        assert v3_player._needs_new_plan(mock_state) is False
    
    def test_needs_new_plan_when_turn_changes(self, v3_player):
        """Should need new plan when turn number changes."""
        mock_plan = Mock(spec=TurnPlan)
        mock_plan.action_sequence = [Mock(), Mock()]
        
        v3_player._current_plan = mock_plan
        v3_player._plan_action_index = 0  # Actions remain
        v3_player._plan_turn_number = 3  # Plan was for turn 3
        
        mock_state = create_mock_game_state(turn_number=5)  # Now turn 5
        assert v3_player._needs_new_plan(mock_state) is True
    
    def test_reset_plan_clears_state(self, v3_player):
        """reset_plan should clear all plan state."""
        v3_player._current_plan = Mock()
        v3_player._plan_action_index = 3
        v3_player._completed_actions = [Mock(), Mock()]
        v3_player._plan_turn_number = 5
        
        v3_player.reset_plan()
        
        assert v3_player._current_plan is None
        assert v3_player._plan_action_index == 0
        assert v3_player._completed_actions == []
        assert v3_player._plan_turn_number is None


class TestActionMatching:
    """Test matching planned actions to valid actions."""
    
    def test_heuristic_matches_play_card(self):
        """Heuristic should match play card actions by name."""
        from game_engine.ai.prompts import find_matching_action_index
        
        planned = PlannedAction(
            action_type="play_card",
            card_name="Rush",
            reasoning="Play Rush for CC",
            cc_cost=0,
            cc_after=5
        )
        
        valid_actions = create_mock_valid_actions([
            ("end_turn", None, "End your turn"),
            ("play_card", "Surge", "Play Surge"),
            ("play_card", "Rush", "Play Rush from hand"),
        ])
        
        index = find_matching_action_index(planned, valid_actions)
        assert index == 2  # Third action is Rush
    
    def test_heuristic_matches_end_turn(self):
        """Heuristic should match end_turn actions."""
        from game_engine.ai.prompts import find_matching_action_index
        
        planned = PlannedAction(
            action_type="end_turn",
            card_name=None,
            reasoning="Done for the turn",
            cc_cost=0,
            cc_after=2
        )
        
        valid_actions = create_mock_valid_actions([
            ("play_card", "Rush", "Play Rush"),
            ("end_turn", None, "End turn"),
        ])
        
        index = find_matching_action_index(planned, valid_actions)
        assert index == 1
    
    def test_heuristic_matches_direct_attack(self):
        """Heuristic should match direct_attack actions."""
        from game_engine.ai.prompts import find_matching_action_index
        
        planned = PlannedAction(
            action_type="direct_attack",
            card_name="Knight",
            reasoning="Attack opponent directly",
            cc_cost=1,
            cc_after=3
        )
        
        valid_actions = create_mock_valid_actions([
            ("end_turn", None, "End turn"),
            ("direct_attack", "Knight", "Direct attack with Knight"),
        ])
        
        index = find_matching_action_index(planned, valid_actions)
        assert index == 1
    
    def test_heuristic_matches_archer_ability(self):
        """Heuristic should match Archer's activate_ability action."""
        from game_engine.ai.prompts import find_matching_action_index
        
        planned = PlannedAction(
            action_type="activate_ability",
            card_name="Archer",
            reasoning="Remove stamina from Knight",
            cc_cost=1,
            cc_after=3
        )
        
        # Real game uses this format for Archer ability
        valid_actions = create_mock_valid_actions([
            ("end_turn", None, "End your turn"),
            ("activate_ability", "Archer", "Archer: Remove 1 stamina - 1 CC"),
        ])
        
        index = find_matching_action_index(planned, valid_actions)
        assert index == 1
    
    def test_heuristic_returns_none_when_no_match(self):
        """Heuristic should return None when no match found."""
        from game_engine.ai.prompts import find_matching_action_index
        
        planned = PlannedAction(
            action_type="play_card",
            card_name="NonexistentCard",
            reasoning="Play it",
            cc_cost=2,
            cc_after=2
        )
        
        valid_actions = create_mock_valid_actions([
            ("play_card", "Rush", "Play Rush"),
            ("play_card", "Surge", "Play Surge"),
        ])
        
        index = find_matching_action_index(planned, valid_actions)
        assert index is None


class TestDecisionInfo:
    """Test get_last_decision_info with v3 plan data."""
    
    @pytest.fixture
    def v3_player(self):
        """Create a V3 player with mocked API."""
        with patch.object(LLMPlayerV3, '__init__', lambda self, **kwargs: None):
            player = LLMPlayerV3.__new__(LLMPlayerV3)
            # v3 attributes
            player._current_plan = None
            player._plan_action_index = 0
            player._completed_actions = []
            player._execution_log = []  # Track execution attempts
            player.turn_planner = None  # Will be None in test context
            # Base LLMPlayer attributes for get_last_decision_info
            player._last_reasoning = "Test"
            player._last_action = None
            player._last_target_ids = None
            player._last_alternative_cost_id = None
            player._last_action_index = None
            player._last_action_number = None
            player._last_prompt = "Test prompt"
            player._last_response = "Test response"
            player._last_raw_response = "Test raw response"
            player.model_name = "test-model"
            return player
    
    def test_decision_info_includes_plan_when_present(self, v3_player):
        """Decision info should include v3_plan when plan exists."""
        mock_plan = Mock(spec=TurnPlan)
        mock_plan.selected_strategy = "Aggressive attack"
        mock_plan.action_sequence = [Mock(), Mock()]
        mock_plan.cc_start = 4
        mock_plan.cc_after_plan = 0
        mock_plan.expected_cards_slept = 2
        mock_plan.cc_efficiency = "2.0"
        
        v3_player._current_plan = mock_plan
        v3_player._plan_action_index = 1
        
        info = v3_player.get_last_decision_info()
        
        assert "v3_plan" in info
        assert info["v3_plan"]["strategy"] == "Aggressive attack"
        assert info["v3_plan"]["total_actions"] == 2
        assert info["v3_plan"]["current_action"] == 1
        assert info["v3_plan"]["cc_efficiency"] == "2.0"
    
    def test_decision_info_no_plan_when_none(self, v3_player):
        """Decision info should not include v3_plan when no plan."""
        v3_player._current_plan = None
        
        info = v3_player.get_last_decision_info()
        
        assert "v3_plan" not in info


class TestTargetExtraction:
    """Test target ID extraction from valid actions."""
    
    def test_uses_planned_targets_when_provided(self):
        """Should use planned targets when provided."""
        from game_engine.ai.prompts import extract_target_from_action
        
        valid_action = Mock()
        valid_action.target_options = []
        
        targets = extract_target_from_action(valid_action, ["card_123", "card_456"])
        assert targets == ["card_123", "card_456"]
    
    def test_extracts_single_target_from_action(self):
        """Should extract single target when action has one option."""
        from game_engine.ai.prompts import extract_target_from_action
        
        target_option = Mock()
        target_option.card_id = "card_123"
        
        valid_action = Mock()
        valid_action.target_options = [target_option]
        
        targets = extract_target_from_action(valid_action, None)
        assert targets == ["card_123"]
    
    def test_returns_none_when_no_targets_available(self):
        """Should return None when no targets available."""
        from game_engine.ai.prompts import extract_target_from_action
        
        valid_action = Mock()
        valid_action.target_options = []
        
        targets = extract_target_from_action(valid_action, None)
        assert targets is None


# Integration test (requires API key - skipped by default)
@pytest.mark.skip(reason="Integration test - requires API key and makes real calls")
class TestV3Integration:
    """Integration tests with real API calls."""
    
    def test_full_turn_flow(self):
        """Test complete turn: plan -> execute -> match."""
        # This would need a real game state and engine
        # Skipped by default, can be run manually for integration testing
        pytest.skip("Integration test requires real game state - run manually")

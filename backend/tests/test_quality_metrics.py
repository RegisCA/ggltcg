"""
Unit tests for quality_metrics.py

Tests the TurnMetrics class and its quality assessment logic.
"""
import pytest
from game_engine.ai.quality_metrics import (
    TurnMetrics,
    record_turn_metrics,
    get_session_metrics,
    get_session_summary,
    clear_session_metrics,
)
from game_engine.ai.prompts import TurnPlan, PlannedAction


class TestTurnMetrics:
    """Test TurnMetrics calculations and properties."""
    
    def test_cc_available_calculation(self):
        """Test that cc_available = cc_start + cc_gained."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
            cc_spent=3,
            cc_remaining=0,
        )
        
        assert metrics.cc_available == 3  # 2 + 1
    
    def test_cc_wasted_equals_remaining(self):
        """Test that cc_wasted is simply cc_remaining."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=0,
            cc_spent=2,
            cc_remaining=2,
        )
        
        assert metrics.cc_wasted == 2
    
    def test_efficiency_rating_optimal(self):
        """Test optimal efficiency (0-1 CC wasted)."""
        # 0 CC wasted
        m1 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
            cc_spent=3,
            cc_remaining=0,
        )
        assert m1.efficiency_rating == "optimal"
        assert m1.is_optimal
        assert not m1.is_wasteful
        
        # 1 CC wasted
        m2 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=0,
            cc_spent=3,
            cc_remaining=1,
        )
        assert m2.efficiency_rating == "optimal"
        assert m2.is_optimal
    
    def test_efficiency_rating_acceptable(self):
        """Test acceptable efficiency (2-3 CC wasted)."""
        # 2 CC wasted
        m1 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=0,
            cc_spent=2,
            cc_remaining=2,
        )
        assert m1.efficiency_rating == "acceptable"
        assert not m1.is_optimal
        assert not m1.is_wasteful
        
        # 3 CC wasted
        m2 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=3,
            cc_start=4,
            cc_gained=1,
            cc_spent=2,
            cc_remaining=3,
        )
        assert m2.efficiency_rating == "acceptable"
    
    def test_efficiency_rating_wasteful(self):
        """Test wasteful efficiency (4+ CC wasted)."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=2,
            cc_spent=2,
            cc_remaining=4,
        )
        
        assert metrics.efficiency_rating == "wasteful"
        assert not metrics.is_optimal
        assert metrics.is_wasteful
    
    def test_expected_cc_for_turn(self):
        """Test expected CC based on turn number."""
        # Turn 1
        m1 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
        )
        assert m1.expected_cc_for_turn == 2
        
        # Turn 2+
        m2 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
        )
        assert m2.expected_cc_for_turn == 4
        
        m3 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=5,
            cc_start=4,
        )
        assert m3.expected_cc_for_turn == 4
    
    def test_expected_min_sleeps(self):
        """Test expected minimum sleeps based on turn and resources."""
        # Turn 1 with Surge (cc_gained > 0)
        m1 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
        )
        assert m1.expected_min_sleeps == 1
        
        # Turn 1 without Surge
        m2 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=0,
        )
        assert m2.expected_min_sleeps == 0
        
        # Turn 2+
        m3 = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
        )
        assert m3.expected_min_sleeps == 1
    
    def test_meets_expectations_wasteful(self):
        """Test that wasteful turns fail expectations."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=0,
            cc_spent=0,
            cc_remaining=4,
            cards_slept=0,
        )
        
        passed, reason = metrics.meets_expectations()
        assert not passed
        assert "Wasteful" in reason
        assert "4 CC unused" in reason
    
    def test_meets_expectations_underperformed_sleeps(self):
        """Test that turns with too few sleeps fail expectations."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=2,
            cc_start=4,
            cc_gained=0,
            cc_spent=3,
            cc_remaining=1,  # Good CC efficiency
            cards_slept=0,  # But no sleeps
        )
        
        passed, reason = metrics.meets_expectations()
        assert not passed
        assert "Underperformed" in reason
        assert "0 sleeps" in reason
    
    def test_meets_expectations_turn1_without_surge(self):
        """Test Turn 1 without Surge is acceptable with 0 sleeps."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=0,  # No Surge
            cc_spent=2,
            cc_remaining=0,
            cards_slept=0,
        )
        
        passed, reason = metrics.meets_expectations()
        assert passed
        # With 0 sleeps expected and 0 sleeps actual, this is "Good"
        assert "Good" in reason
        assert "2/2 CC" in reason
    
    def test_meets_expectations_good_turn(self):
        """Test a good turn passes expectations."""
        metrics = TurnMetrics(
            game_id="test",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
            cc_spent=3,
            cc_remaining=0,
            cards_slept=1,
        )
        
        passed, reason = metrics.meets_expectations()
        assert passed
        assert "Good" in reason
        assert "3/3 CC" in reason
        assert "1 sleeps" in reason
    
    def test_to_log_dict(self):
        """Test conversion to log dictionary."""
        metrics = TurnMetrics(
            game_id="game123",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
            cc_spent=3,
            cc_remaining=0,
            cards_slept=1,
        )
        
        log_dict = metrics.to_log_dict()
        
        assert log_dict["game_id"] == "game123"
        assert log_dict["turn"] == 1
        assert log_dict["cc_start"] == 2
        assert log_dict["cc_gained"] == 1
        assert log_dict["cc_spent"] == 3
        assert log_dict["cc_remaining"] == 0
        assert log_dict["cc_wasted"] == 0
        assert log_dict["efficiency_pct"] == 100.0
        assert log_dict["efficiency_rating"] == "optimal"
        assert log_dict["cards_slept"] == 1
        assert log_dict["meets_expectations"] is True
        assert "Good" in log_dict["assessment"]


class TestTurnMetricsFromPlan:
    """Test extracting metrics from TurnPlan objects."""
    
    def test_from_plan_with_surge(self):
        """Test extracting metrics from plan with Surge."""
        # Mock game state
        class MockGameState:
            game_id = "test_game"
            turn_number = 1
        
        # Create plan with Surge
        plan = TurnPlan(
            threat_assessment="Test",
            resources_summary="Test",
            sequences_considered=[],
            selected_strategy="Test",
            action_sequence=[
                PlannedAction(
                    action_type="play_card",
                    card_id="surge1",
                    card_name="Surge",
                    cc_cost=0,
                    cc_after=3,
                    reasoning="Gain CC",
                ),
                PlannedAction(
                    action_type="play_card",
                    card_id="knight1",
                    card_name="Knight",
                    cc_cost=1,
                    cc_after=2,
                    reasoning="Play toy",
                ),
                PlannedAction(
                    action_type="end_turn",
                    cc_cost=0,
                    cc_after=2,
                    reasoning="End",
                ),
            ],
            cc_start=2,
            cc_after_plan=2,
            expected_cards_slept=0,
            cc_efficiency="N/A",
            plan_reasoning="Test",
        )
        
        metrics = TurnMetrics.from_plan(plan, MockGameState(), "player1")
        
        assert metrics.game_id == "test_game"
        assert metrics.turn_number == 1
        assert metrics.cc_start == 2
        assert metrics.cc_gained == 1  # From Surge
        assert metrics.cc_remaining == 2
        assert metrics.toys_played == 1  # Knight
        assert metrics.actions_taken == 2  # Surge + Knight (not end_turn)
    
    def test_from_plan_with_rush(self):
        """Test extracting metrics from plan with Rush."""
        class MockGameState:
            game_id = "test_game"
            turn_number = 2
        
        plan = TurnPlan(
            threat_assessment="Test",
            resources_summary="Test",
            sequences_considered=[],
            selected_strategy="Test",
            action_sequence=[
                PlannedAction(
                    action_type="play_card",
                    card_id="rush1",
                    card_name="Rush",
                    cc_cost=0,
                    cc_after=6,
                    reasoning="Gain CC",
                ),
            ],
            cc_start=4,
            cc_after_plan=6,
            expected_cards_slept=0,
            cc_efficiency="N/A",
            plan_reasoning="Test",
        )
        
        metrics = TurnMetrics.from_plan(plan, MockGameState(), "player1")
        
        assert metrics.cc_gained == 2  # From Rush
        assert metrics.toys_played == 0  # Rush is an action card


class TestSessionMetrics:
    """Test session-level metrics tracking."""
    
    def setup_method(self):
        """Clear session metrics before each test."""
        clear_session_metrics()
    
    def test_record_and_retrieve_metrics(self):
        """Test recording and retrieving session metrics."""
        m1 = TurnMetrics(
            game_id="game1",
            player_id="player1",
            turn_number=1,
            cc_start=2,
            cc_gained=1,
            cc_spent=3,
            cc_remaining=0,
            cards_slept=1,
        )
        
        record_turn_metrics(m1)
        
        session = get_session_metrics()
        assert len(session) == 1
        assert session[0].turn_number == 1
    
    def test_session_summary_empty(self):
        """Test session summary with no metrics."""
        summary = get_session_summary()
        assert summary["turns"] == 0
        assert "message" in summary
    
    def test_session_summary_with_metrics(self):
        """Test session summary calculations."""
        # Record 3 turns: 2 optimal, 1 wasteful
        record_turn_metrics(TurnMetrics(
            game_id="game1", player_id="player1", turn_number=1,
            cc_start=2, cc_gained=1, cc_spent=3, cc_remaining=0,
            cards_slept=1,
        ))
        record_turn_metrics(TurnMetrics(
            game_id="game1", player_id="player1", turn_number=2,
            cc_start=4, cc_gained=0, cc_spent=3, cc_remaining=1,
            cards_slept=1,
        ))
        record_turn_metrics(TurnMetrics(
            game_id="game1", player_id="player1", turn_number=3,
            cc_start=4, cc_gained=0, cc_spent=0, cc_remaining=4,
            cards_slept=0,
        ))
        
        summary = get_session_summary()
        
        assert summary["turns"] == 3
        assert summary["optimal_turns"] == 2
        assert summary["optimal_pct"] == pytest.approx(66.7, abs=0.1)
        assert summary["wasteful_turns"] == 1
        assert summary["wasteful_pct"] == pytest.approx(33.3, abs=0.1)
        assert summary["avg_cc_wasted"] == pytest.approx(1.67, abs=0.01)  # (0+1+4)/3
        assert summary["avg_cards_slept"] == pytest.approx(0.67, abs=0.01)  # (1+1+0)/3
    
    def test_clear_session_metrics(self):
        """Test clearing session metrics."""
        record_turn_metrics(TurnMetrics(
            game_id="game1", player_id="player1", turn_number=1,
            cc_start=2, cc_spent=2, cc_remaining=0,
        ))
        
        assert len(get_session_metrics()) == 1
        
        clear_session_metrics()
        
        assert len(get_session_metrics()) == 0
        summary = get_session_summary()
        assert summary["turns"] == 0

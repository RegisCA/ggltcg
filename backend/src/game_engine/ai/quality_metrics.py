"""
Turn-level quality metrics for AI V4.

These metrics provide objective measurement of AI sequence quality.
CC waste is the primary quality indicator - advanced players waste <1 CC per turn.

Usage:
    metrics = TurnMetrics.from_plan(plan, game_state, player_id)
    if metrics.is_wasteful:
        logger.warning(f"Wasteful turn: {metrics.cc_wasted} CC wasted")
"""
from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime
import logging
import threading

logger = logging.getLogger("game_engine.ai.quality_metrics")


@dataclass
class TurnMetrics:
    """Metrics for a single AI turn."""
    # Context
    game_id: str
    player_id: str
    turn_number: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    # CC metrics
    cc_start: int = 0
    cc_gained: int = 0  # From Surge, Rush, etc.
    cc_spent: int = 0
    cc_remaining: int = 0
    
    # Outcome metrics
    cards_slept: int = 0
    toys_played: int = 0
    actions_taken: int = 0
    
    # Efficiency calculations
    @property
    def cc_available(self) -> int:
        """Total CC available this turn (start + gained)."""
        return self.cc_start + self.cc_gained
    
    @property
    def cc_wasted(self) -> int:
        """CC left unused at end of turn."""
        return self.cc_remaining
    
    @property
    def efficiency_pct(self) -> float:
        """Percentage of available CC that was used."""
        if self.cc_available == 0:
            return 100.0
        return (self.cc_spent / self.cc_available) * 100
    
    @property
    def efficiency_rating(self) -> str:
        """
        Rate turn efficiency.
        
        Based on advanced player benchmarks:
        - 0-1 CC wasted = optimal
        - 2-3 CC wasted = acceptable (strategic save)
        - 4+ CC wasted = wasteful
        """
        if self.cc_wasted <= 1:
            return "optimal"
        elif self.cc_wasted <= 3:
            return "acceptable"
        else:
            return "wasteful"
    
    @property
    def is_optimal(self) -> bool:
        return self.efficiency_rating == "optimal"
    
    @property
    def is_wasteful(self) -> bool:
        return self.efficiency_rating == "wasteful"
    
    # Turn-specific expectations
    @property
    def expected_cc_for_turn(self) -> int:
        """Expected CC budget based on turn number."""
        if self.turn_number == 1:
            return 2  # Turn 1 starts with 2 CC
        else:
            return 4  # Turn 2+ starts with 4 CC (capped at 7)
    
    @property
    def expected_min_sleeps(self) -> int:
        """
        Expected minimum cards slept based on turn.
        
        Turn 1: With Surge+Knight+direct_attack = 1 sleep possible
        Turn 2+: With 4 CC = 2 sleeps possible (toy + 2 attacks)
        """
        if self.turn_number == 1:
            return 1 if self.cc_gained > 0 else 0  # Need Surge to sleep on T1
        else:
            return 1  # At minimum should sleep 1 card on T2+
    
    def meets_expectations(self) -> Tuple[bool, str]:
        """
        Check if turn meets minimum quality expectations.
        
        Returns:
            (passed, reason) tuple
        """
        # Check CC waste
        if self.is_wasteful:
            return False, f"Wasteful: {self.cc_wasted} CC unused (max 3 acceptable)"
        
        # Check minimum sleeps (soft check - some turns may be setup)
        if self.cards_slept < self.expected_min_sleeps:
            # Special case: Turn 1 without Surge can't sleep
            if self.turn_number == 1 and self.cc_gained == 0:
                return True, "Turn 1 without Surge - no sleep expected"
            return False, f"Underperformed: {self.cards_slept} sleeps vs {self.expected_min_sleeps} expected"
        
        return True, f"Good: {self.cc_spent}/{self.cc_available} CC, {self.cards_slept} sleeps"
    
    @classmethod
    def from_plan(cls, plan, game_state, player_id: str) -> "TurnMetrics":
        """
        Extract metrics from a completed plan.
        
        Args:
            plan: TurnPlan object from turn_planner
            game_state: Current GameState
            player_id: Player who made the plan
        """
        # Count CC gains from the plan
        cc_gained = 0
        toys_played = 0
        
        for action in plan.action_sequence:
            if action.action_type == "play_card":
                if action.card_name == "Surge":
                    cc_gained += 1
                elif action.card_name == "Rush":
                    cc_gained += 2
                # Check if it's a toy (simplified - would need card lookup for accuracy)
                # TODO(Phase 5): Replace with ID-based card lookups using card_type metadata
                if action.card_name not in ["Surge", "Rush", "Wake", "Drop", "Clean", "Twist", "Sun", "Copy", "Toynado"]:
                    toys_played += 1
        
        return cls(
            game_id=game_state.game_id,
            player_id=player_id,
            turn_number=game_state.turn_number,
            cc_start=plan.cc_start,
            cc_gained=cc_gained,
            cc_spent=plan.cc_start + cc_gained - (plan.cc_after_plan or 0),
            cc_remaining=plan.cc_after_plan or 0,
            cards_slept=plan.expected_cards_slept,
            toys_played=toys_played,
            actions_taken=len([a for a in plan.action_sequence if a.action_type != "end_turn"]),
        )
    
    def to_log_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        passed, reason = self.meets_expectations()
        return {
            "game_id": self.game_id,
            "turn": self.turn_number,
            "cc_start": self.cc_start,
            "cc_gained": self.cc_gained,
            "cc_spent": self.cc_spent,
            "cc_remaining": self.cc_remaining,
            "cc_wasted": self.cc_wasted,
            "efficiency_pct": round(self.efficiency_pct, 1),
            "efficiency_rating": self.efficiency_rating,
            "cards_slept": self.cards_slept,
            "meets_expectations": passed,
            "assessment": reason,
        }


# Global metrics storage for session analysis
# NOTE: For single-threaded testing/development only. Not thread-safe for parallel simulations.
_session_metrics: List[TurnMetrics] = []
_metrics_lock = threading.Lock()


def record_turn_metrics(metrics: TurnMetrics):
    """Record metrics for later analysis. Thread-safe for concurrent access."""
    with _metrics_lock:
        _session_metrics.append(metrics)
    
    # Log immediately
    log_data = metrics.to_log_dict()
    if metrics.is_wasteful:
        logger.warning(f"WASTEFUL TURN: {log_data}")
    elif not metrics.meets_expectations()[0]:
        logger.info(f"SUBOPTIMAL TURN: {log_data}")
    else:
        logger.info(f"GOOD TURN: {log_data}")


def get_session_metrics() -> List[TurnMetrics]:
    """Get all metrics from current session. Thread-safe."""
    with _metrics_lock:
        return _session_metrics.copy()


def get_session_summary() -> dict:
    """Get summary statistics for the session. Thread-safe."""
    with _metrics_lock:
        if not _session_metrics:
            return {"turns": 0, "message": "No turns recorded"}
        
        total = len(_session_metrics)
        optimal = sum(1 for m in _session_metrics if m.is_optimal)
        wasteful = sum(1 for m in _session_metrics if m.is_wasteful)
        avg_waste = sum(m.cc_wasted for m in _session_metrics) / total
        avg_sleeps = sum(m.cards_slept for m in _session_metrics) / total
        
        return {
            "turns": total,
            "optimal_turns": optimal,
            "optimal_pct": round(optimal / total * 100, 1),
            "wasteful_turns": wasteful,
            "wasteful_pct": round(wasteful / total * 100, 1),
            "avg_cc_wasted": round(avg_waste, 2),
            "avg_cards_slept": round(avg_sleeps, 2),
            "target_avg_waste": "< 1.0",
            "target_optimal_pct": "> 65%",
        }


def clear_session_metrics():
    """Clear metrics for new session. Thread-safe."""
    global _session_metrics
    with _metrics_lock:
        _session_metrics = []

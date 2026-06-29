"""
Turn-level quality metrics for AI V4.

These metrics provide objective measurement of AI sequence quality.
Charge waste is the primary quality indicator - advanced players waste <1 Charge per turn.

Usage:
    metrics = TurnMetrics.from_plan(plan, game_state, player_id)
    if metrics.is_wasteful:
        logger.warning(f"Wasteful turn: {metrics.charge_wasted} Charge wasted")
"""
from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime
import logging
import threading

from .card_metadata import ACTION_CARD_NAMES, CHARGE_GAIN_ON_PLAY

logger = logging.getLogger("game_engine.ai.quality_metrics")


@dataclass
class TurnMetrics:
    """Metrics for a single AI turn."""
    # Context
    game_id: str
    player_id: str
    turn_number: int
    timestamp: datetime = field(default_factory=datetime.now)

    # Charge metrics
    charge_start: int = 0
    charge_gained: int = 0  # From Surge, Rush, etc.
    charge_spent: int = 0
    charge_remaining: int = 0

    # Outcome metrics
    cards_broken: int = 0
    toys_played: int = 0
    actions_taken: int = 0

    # Efficiency calculations
    @property
    def charge_available(self) -> int:
        """Total Charge available this turn (start + gained)."""
        return self.charge_start + self.charge_gained

    @property
    def charge_wasted(self) -> int:
        """Charge left unused at end of turn."""
        return self.charge_remaining

    @property
    def efficiency_pct(self) -> float:
        """Percentage of available Charge that was used."""
        if self.charge_available == 0:
            return 100.0
        return (self.charge_spent / self.charge_available) * 100

    @property
    def efficiency_rating(self) -> str:
        """
        Rate turn efficiency.

        Based on advanced player benchmarks:
        - 0-1 Charge wasted = optimal
        - 2-3 Charge wasted = acceptable (strategic save)
        - 4+ Charge wasted = wasteful
        """
        if self.charge_wasted <= 1:
            return "optimal"
        elif self.charge_wasted <= 3:
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
    def expected_charge_for_turn(self) -> int:
        """Expected Charge budget based on turn number."""
        if self.turn_number == 1:
            return 2  # Turn 1 starts with 2 Charge
        else:
            return 4  # Turn 2+ starts with 4 Charge (capped at 7)

    @property
    def expected_min_breaks(self) -> int:
        """
        Expected minimum cards broken based on turn.

        Turn 1: With Surge+Knight+direct_attack = 1 break possible
        Turn 2+: With 4 Charge = 2 breaks possible (toy + 2 attacks)
        """
        if self.turn_number == 1:
            return 1 if self.charge_gained > 0 else 0  # Need Surge to break on T1
        else:
            return 1  # At minimum should break 1 card on T2+

    def meets_expectations(self) -> Tuple[bool, str]:
        """
        Check if turn meets minimum quality expectations.

        Returns:
            (passed, reason) tuple
        """
        # Check Charge waste
        if self.is_wasteful:
            return False, f"Wasteful: {self.charge_wasted} Charge unused (max 3 acceptable)"

        # Check minimum breaks (soft check - some turns may be setup)
        if self.cards_broken < self.expected_min_breaks:
            # Special case: Turn 1 without Surge can't break
            if self.turn_number == 1 and self.charge_gained == 0:
                return True, "Turn 1 without Surge - no break expected"
            return False, f"Underperformed: {self.cards_broken} breaks vs {self.expected_min_breaks} expected"

        return True, f"Good: {self.charge_spent}/{self.charge_available} Charge, {self.cards_broken} breaks"

    @classmethod
    def from_plan(cls, plan, game_state, player_id: str) -> "TurnMetrics":
        """
        Extract metrics from a completed plan.

        Args:
            plan: TurnPlan object from turn_planner
            game_state: Current GameState
            player_id: Player who made the plan
        """
        # Count Charge gains from the plan
        charge_gained = 0
        toys_played = 0

        for action in plan.action_sequence:
            if action.action_type == "play_card":
                charge_gained += CHARGE_GAIN_ON_PLAY.get(action.card_name, 0)
                if action.card_name not in ACTION_CARD_NAMES:
                    toys_played += 1

        return cls(
            game_id=game_state.game_id,
            player_id=player_id,
            turn_number=game_state.turn_number,
            charge_start=plan.charge_start,
            charge_gained=charge_gained,
            charge_spent=plan.charge_start + charge_gained - (plan.charge_after_plan or 0),
            charge_remaining=plan.charge_after_plan or 0,
            cards_broken=plan.expected_cards_broken,
            toys_played=toys_played,
            actions_taken=len([a for a in plan.action_sequence if a.action_type != "end_turn"]),
        )

    def to_log_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        passed, reason = self.meets_expectations()
        return {
            "game_id": self.game_id,
            "turn": self.turn_number,
            "charge_start": self.charge_start,
            "charge_gained": self.charge_gained,
            "charge_spent": self.charge_spent,
            "charge_remaining": self.charge_remaining,
            "charge_wasted": self.charge_wasted,
            "efficiency_pct": round(self.efficiency_pct, 1),
            "efficiency_rating": self.efficiency_rating,
            "cards_broken": self.cards_broken,
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
        avg_waste = sum(m.charge_wasted for m in _session_metrics) / total
        avg_breaks = sum(m.cards_broken for m in _session_metrics) / total

        return {
            "turns": total,
            "optimal_turns": optimal,
            "optimal_pct": round(optimal / total * 100, 1),
            "wasteful_turns": wasteful,
            "wasteful_pct": round(wasteful / total * 100, 1),
            "avg_charge_wasted": round(avg_waste, 2),
            "avg_cards_broken": round(avg_breaks, 2),
            "target_avg_waste": "< 1.0",
            "target_optimal_pct": "> 65%",
        }


def clear_session_metrics():
    """Clear metrics for new session. Thread-safe."""
    global _session_metrics
    with _metrics_lock:
        _session_metrics = []

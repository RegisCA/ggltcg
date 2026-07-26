"""An AI player that makes zero API calls.

``LLMPlayer`` reaches the network in exactly two places: ``TurnPlanner`` asking
Gemini which enumerated sequence to play, and the rare execution-matching call
when heuristic action matching fails. Both are replaced here, so everything else
— enumeration, plan conversion, plan execution, replanning — runs the same code
paths a live game does. That fidelity is the point: a sweep measures the real
engine, not a reimplementation of it.

Cost is CPU only, roughly 550 ms per game on an M1, which makes 10^5-scale runs
practical for card evaluation.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Optional

from game_engine.ai.llm_player import LLMPlayer
from game_engine.ai.turn_planner import TurnPlanner

from .policies import SelectionPolicy, get_policy

logger = logging.getLogger(__name__)


class ScriptedSelectionError(RuntimeError):
    """Raised when the scripted player is asked to make an LLM call."""


class ScriptedTurnPlanner(TurnPlanner):
    """``TurnPlanner`` with the Gemini selection step swapped for a local policy."""

    def __init__(self, policy: SelectionPolicy, rng: random.Random,
                 max_actions: Optional[int] = None,
                 max_sequences: Optional[int] = None):
        # Deliberately skips TurnPlanner.__init__: it builds a provider client,
        # which needs an API key and would open a network-capable session for a
        # player that must never make a request.
        self.policy = policy
        self.rng = rng
        self.enum_max_actions = max_actions
        self.enum_max_sequences = max_sequences
        self.client = None
        self.provider_client = None
        self.model_name = f"scripted:{policy.name}"
        self.fallback_model = None
        self._last_plan = None
        self._last_prompt = None
        self._last_response = None
        self._selection_prompt = None
        self._selection_response = None
        self._selection_system_instruction = None
        self._enum_debug: dict = {}

    def _select_sequence(self, sequences, game_state, player_id, game_engine=None):
        index = self.policy(sequences, game_state, player_id, self.rng)
        return index, f"[{self.policy.name}] sequence {index}"


class ScriptedPlayer(LLMPlayer):
    """Drop-in replacement for ``LLMPlayer`` that plays without a provider.

    Args:
        policy: Policy name from ``simulation.policies`` (e.g. ``"greedy"``).
        seed: Seeds this player's RNG. Games must pass a distinct, recorded seed
            per game so a run can be replayed exactly — the engine's own
            ``random.choice`` on direct attacks is the other variance source and
            is seeded by the sweep driver.
    """

    def __init__(self, policy: str = "greedy", seed: int = 0,
                 max_actions: Optional[int] = None,
                 max_sequences: Optional[int] = None):
        self.policy_name = policy
        self.rng = random.Random(seed)
        self.provider_client = None
        self.api_key = None
        self.model_name = f"scripted:{policy}"
        self.fallback_model = None
        self.client = None

        # Plan state — mirrors LLMPlayer.__init__ without the provider setup.
        self._current_plan = None
        self._plan_action_index = 0
        self._completed_actions = []
        self._plan_turn_number = None
        self._execution_log = []
        self._midturn_replan_count = 0
        self._last_target_ids = None
        self._last_alternative_cost_id = None

        # Counts turns where heuristic action matching failed and a live player
        # would have spent an LLM call. Should stay near zero, since the plan is
        # built from sequences the engine itself enumerated; a rising count means
        # plan-to-action matching has drifted and the sweep is quietly degrading.
        self.execution_fallbacks = 0

        self.turn_planner = ScriptedTurnPlanner(
            get_policy(policy), self.rng,
            max_actions=max_actions, max_sequences=max_sequences,
        )

    def _call_execution_api(self, prompt: str) -> str:
        """Never call out. Raising routes into the existing plan-failure path,
        which ends the turn safely rather than inventing an action."""
        self.execution_fallbacks += 1
        raise ScriptedSelectionError(
            "ScriptedPlayer cannot resolve an action via LLM; ending turn instead"
        )

    def get_endpoint_name(self) -> str:
        return f"Scripted ({self.policy_name})"

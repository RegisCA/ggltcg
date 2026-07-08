"""
Tests for PR B2: threading the rate limiter through the Gemini call path.

Covers:
- GeminiProvider.acquire() is called once per generate_content attempt,
  including retries and the fallback-model recursion path.
- BudgetExhaustedError from the limiter propagates immediately out of
  generate_json/generate_text (no retry, no fallback, no swallowing).
- Default behavior (no rate_limiter passed) is unchanged: a NoopLimiter is
  used and never blocks or raises.
- The rate_limiter constructor arg is forwarded: build_provider -> GeminiProvider,
  LLMPlayer -> build_provider, SimulationRunner -> LLMPlayer (both players).
- BudgetExhaustedError propagates out of LLMPlayer and out of
  SimulationRunner.run_game (not swallowed into a fake draw).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.ai.providers import (  # noqa: E402
    AIProviderConfig,
    GeminiProvider,
    build_provider,
)
from game_engine.ai.llm_player import LLMPlayer  # noqa: E402
from game_engine.ai.rate_limiter import BudgetExhaustedError, NoopLimiter  # noqa: E402
import simulation.runner as runner_module  # noqa: E402
from simulation.runner import SimulationRunner  # noqa: E402


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


class CountingLimiter:
    """Fake limiter that records every acquire() call."""

    def __init__(self):
        self.acquire_count = 0

    def acquire(self):
        self.acquire_count += 1

    def remaining(self):
        return {}

    def flush(self):
        pass


class ExhaustedLimiter:
    """Fake limiter that always raises BudgetExhaustedError immediately."""

    def acquire(self):
        raise BudgetExhaustedError(resets_at=datetime.now(timezone.utc))

    def remaining(self):
        return {}

    def flush(self):
        pass


class RetryThenSucceedClient:
    """Fake google-genai client: raises a 429-style error `fail_times`
    times, then returns a canned successful response."""

    def __init__(self, fail_times: int, text: str = '{"ok": true}'):
        self.fail_times = fail_times
        self.calls = 0
        self.text = text
        self.models = SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise Exception("429 Resource exhausted")
        candidate = MagicMock()
        candidate.content.parts = [MagicMock()]
        response = MagicMock()
        response.candidates = [candidate]
        response.text = self.text
        return response


class AlwaysFailClient:
    """Fake client whose generate_content always raises a retryable error,
    used to exercise the fallback-model recursion path."""

    def __init__(self):
        self.calls = 0
        self.models = SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, **kwargs):
        self.calls += 1
        raise Exception("429 Resource exhausted")


def _config():
    return AIProviderConfig(api_key="dummy", model="model-a", fallback_model="model-b")


# --------------------------------------------------------------------------
# GeminiProvider: acquire() called once per attempt, including retries
# --------------------------------------------------------------------------


class TestGeminiProviderRateLimiting:
    def test_default_rate_limiter_is_noop(self):
        provider = GeminiProvider(_config(), client=RetryThenSucceedClient(fail_times=0))
        assert isinstance(provider.rate_limiter, NoopLimiter)

    def test_acquire_called_once_per_successful_attempt(self):
        limiter = CountingLimiter()
        client = RetryThenSucceedClient(fail_times=0)
        provider = GeminiProvider(_config(), client=client, rate_limiter=limiter)

        result = provider.generate_json(
            "prompt", {}, temperature=0.1, max_output_tokens=100
        )

        assert result == '{"ok": true}'
        assert limiter.acquire_count == 1
        assert client.calls == 1

    def test_acquire_called_for_each_retry(self, monkeypatch):
        # Avoid real sleeping between retries.
        monkeypatch.setattr("game_engine.ai.providers.time.sleep", lambda _s: None)

        limiter = CountingLimiter()
        client = RetryThenSucceedClient(fail_times=2)
        provider = GeminiProvider(_config(), client=client, rate_limiter=limiter)

        result = provider.generate_json(
            "prompt", {}, temperature=0.1, max_output_tokens=100, retry_count=3
        )

        assert result == '{"ok": true}'
        # Two failed attempts + one successful attempt = 3 acquires, 3 client calls.
        assert limiter.acquire_count == 3
        assert client.calls == 3

    def test_acquire_called_on_fallback_path(self, monkeypatch):
        monkeypatch.setattr("game_engine.ai.providers.time.sleep", lambda _s: None)

        limiter = CountingLimiter()
        client = AlwaysFailClient()
        provider = GeminiProvider(_config(), client=client, rate_limiter=limiter)

        with pytest.raises(Exception, match="429"):
            provider.generate_json(
                "prompt", {}, temperature=0.1, max_output_tokens=100, retry_count=2
            )

        # retry_count=2 exhausts retries on the primary model (2 acquires/calls),
        # then falls back to the fallback model with retry_count=1 (1 more
        # acquire/call) before finally raising.
        assert limiter.acquire_count == 3
        assert client.calls == 3

    def test_generate_text_also_acquires_per_attempt(self, monkeypatch):
        monkeypatch.setattr("game_engine.ai.providers.time.sleep", lambda _s: None)

        limiter = CountingLimiter()
        client = RetryThenSucceedClient(fail_times=1, text="hello")
        provider = GeminiProvider(_config(), client=client, rate_limiter=limiter)

        result = provider.generate_text(
            "prompt", temperature=0.1, max_output_tokens=100, retry_count=3
        )

        assert result == "hello"
        assert limiter.acquire_count == 2
        assert client.calls == 2


# --------------------------------------------------------------------------
# BudgetExhaustedError: propagates immediately, no retry, no fallback
# --------------------------------------------------------------------------


class TestBudgetExhaustedPropagation:
    def test_generate_json_propagates_immediately(self):
        client = RetryThenSucceedClient(fail_times=0)
        provider = GeminiProvider(_config(), client=client, rate_limiter=ExhaustedLimiter())

        with pytest.raises(BudgetExhaustedError):
            provider.generate_json("prompt", {}, temperature=0.1, max_output_tokens=100, retry_count=3)

        # The client should never even be called: acquire() raises before
        # generate_content is attempted.
        assert client.calls == 0

    def test_generate_text_propagates_immediately(self):
        client = RetryThenSucceedClient(fail_times=0)
        provider = GeminiProvider(_config(), client=client, rate_limiter=ExhaustedLimiter())

        with pytest.raises(BudgetExhaustedError):
            provider.generate_text("prompt", temperature=0.1, max_output_tokens=100, retry_count=3)

        assert client.calls == 0

    def test_build_provider_forwards_rate_limiter(self):
        limiter = CountingLimiter()
        provider, _config_out = build_provider(
            api_key="dummy",
            client=RetryThenSucceedClient(fail_times=0),
            rate_limiter=limiter,
        )
        assert provider.rate_limiter is limiter


# --------------------------------------------------------------------------
# LLMPlayer: forwards rate_limiter to build_provider; propagates the error
# --------------------------------------------------------------------------


class TestLLMPlayerRateLimiterForwarding(object):
    def test_llm_player_forwards_rate_limiter_to_build_provider(self, monkeypatch):
        captured = {}

        def fake_build_provider(**kwargs):
            captured.update(kwargs)
            fake_provider = MagicMock()
            fake_provider.client = None
            return fake_provider, AIProviderConfig(api_key="k", model="m", fallback_model="m")

        monkeypatch.setattr("game_engine.ai.llm_player.build_provider", fake_build_provider)

        sentinel = CountingLimiter()
        player = LLMPlayer(model="m", rate_limiter=sentinel)

        assert captured.get("rate_limiter") is sentinel
        assert player.provider_client is not None

    def test_budget_exhausted_propagates_out_of_llm_player_execution_call(self, monkeypatch):
        def fake_build_provider(**kwargs):
            fake_provider = MagicMock()
            fake_provider.client = None
            fake_provider.generate_json.side_effect = BudgetExhaustedError(resets_at=datetime.now(timezone.utc))
            return fake_provider, AIProviderConfig(api_key="k", model="m", fallback_model="m")

        monkeypatch.setattr("game_engine.ai.llm_player.build_provider", fake_build_provider)

        player = LLMPlayer(model="m", rate_limiter=ExhaustedLimiter())

        with pytest.raises(BudgetExhaustedError):
            player._call_execution_api("some prompt")


# --------------------------------------------------------------------------
# SimulationRunner: forwards rate_limiter to both LLMPlayer constructions;
# BudgetExhaustedError propagates out of run_game instead of becoming a draw.
# --------------------------------------------------------------------------


class FakeLLMPlayer:
    """Records constructor kwargs so we can assert rate_limiter forwarding."""

    instances = []

    def __init__(self, api_key=None, model=None, rate_limiter=None):
        self.model = model
        self.rate_limiter = rate_limiter
        FakeLLMPlayer.instances.append(self)


class FakeGameEngine:
    def __init__(self, game_state):
        self.game_state = game_state

    def start_turn(self):
        pass

    def check_state_based_actions(self):
        pass


class TestSimulationRunnerRateLimiterForwarding:
    def setup_method(self):
        FakeLLMPlayer.instances = []

    def test_run_game_forwards_rate_limiter_to_both_players(self, monkeypatch):
        sentinel = CountingLimiter()

        monkeypatch.setattr(runner_module, "LLMPlayer", FakeLLMPlayer)
        monkeypatch.setattr(runner_module, "GameEngine", FakeGameEngine)
        monkeypatch.setattr(
            SimulationRunner,
            "_create_game_state",
            lambda self, deck1, deck2: SimpleNamespace(winner_id="player1", turn_number=1),
        )

        runner = SimulationRunner(rate_limiter=sentinel)
        result = runner.run_game(
            deck1=SimpleNamespace(name="deck1", cards=[]),
            deck2=SimpleNamespace(name="deck2", cards=[]),
            game_number=1,
        )

        assert len(FakeLLMPlayer.instances) == 2
        assert all(inst.rate_limiter is sentinel for inst in FakeLLMPlayer.instances)
        assert result.outcome.value == "player1_win"

    def test_default_rate_limiter_is_none_and_forwarded_as_none(self, monkeypatch):
        monkeypatch.setattr(runner_module, "LLMPlayer", FakeLLMPlayer)
        monkeypatch.setattr(runner_module, "GameEngine", FakeGameEngine)
        monkeypatch.setattr(
            SimulationRunner,
            "_create_game_state",
            lambda self, deck1, deck2: SimpleNamespace(winner_id="player1", turn_number=1),
        )

        runner = SimulationRunner()
        runner.run_game(
            deck1=SimpleNamespace(name="deck1", cards=[]),
            deck2=SimpleNamespace(name="deck2", cards=[]),
            game_number=1,
        )

        assert all(inst.rate_limiter is None for inst in FakeLLMPlayer.instances)

    def test_budget_exhausted_propagates_out_of_run_game(self, monkeypatch):
        def raise_exhausted(self, deck1, deck2):
            raise BudgetExhaustedError(resets_at=datetime.now(timezone.utc))

        monkeypatch.setattr(runner_module, "LLMPlayer", FakeLLMPlayer)
        monkeypatch.setattr(runner_module, "GameEngine", FakeGameEngine)
        monkeypatch.setattr(SimulationRunner, "_create_game_state", raise_exhausted)

        runner = SimulationRunner(rate_limiter=CountingLimiter())

        with pytest.raises(BudgetExhaustedError):
            runner.run_game(
                deck1=SimpleNamespace(name="deck1", cards=[]),
                deck2=SimpleNamespace(name="deck2", cards=[]),
                game_number=1,
            )


class TestBudgetExhaustionNotSwallowedByPlanner:
    """Regression: the E2E run on 2026-07-08 showed BudgetExhaustedError being
    swallowed by TurnPlanner/LLMPlayer broad except handlers ("Strategic
    selection failed"), so exhausted runs finished with heuristic no-LLM games
    instead of pausing. These pin the raise at the planner/player layer."""

    def test_turn_planner_create_plan_propagates_budget_exhaustion(self):
        from conftest import create_game_with_cards
        from game_engine.ai.turn_planner import TurnPlanner

        class ExhaustedSelector:
            def generate_json(self, prompt, schema, **kwargs):
                raise BudgetExhaustedError(resets_at=datetime.now(timezone.utc))

            def get_display_name(self, model):  # pragma: no cover - cosmetic
                return "stub"

        setup, _ = create_game_with_cards(
            player1_in_play=["Raggy"],
            player2_in_play=["Gibbers"],
            player2_hand=["Ka"],
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=3,
        )
        planner = TurnPlanner(
            client=None, model_name="m", fallback_model="f",
            provider_client=ExhaustedSelector(),
        )

        with pytest.raises(BudgetExhaustedError):
            planner.create_plan(setup.game_state, "player1", setup.engine)

    def test_generic_selection_failure_still_falls_back(self):
        """The broad-except fallback must keep working for non-budget errors."""
        from conftest import create_game_with_cards
        from game_engine.ai.turn_planner import TurnPlanner

        class BrokenSelector:
            def generate_json(self, prompt, schema, **kwargs):
                raise ValueError("parse boom")

            def get_display_name(self, model):  # pragma: no cover - cosmetic
                return "stub"

        setup, _ = create_game_with_cards(
            player1_in_play=["Raggy"],
            player2_in_play=["Gibbers"],
            player2_hand=["Ka"],
            player1_charge=2,
            player2_charge=0,
            active_player="player1",
            turn_number=3,
        )
        planner = TurnPlanner(
            client=None, model_name="m", fallback_model="f",
            provider_client=BrokenSelector(),
        )

        plan = planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None, "non-budget failures must still fall back to first sequence"

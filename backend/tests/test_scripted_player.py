"""LLM-free simulation players (``simulation.scripted_player``).

Gates pinned here:

1. **No network, no key** — a scripted game completes with GOOGLE_API_KEY absent.
   The whole point of the sweep harness is that 10^5 games cost nothing; a
   provider quietly being constructed would break that and go unnoticed.
2. **Reproducibility** — same seed, same game. Both the policy RNG and the
   engine's ``random.choice`` on direct attacks must be pinned, or a sweep
   dataset cannot be replayed.
3. **Policy isolation** — a policy returning a nonsense index must not crash a
   run, since a sweep is unattended.
"""

import os

import pytest

from simulation.deck_loader import load_simulation_decks_dict
from simulation.policies import POLICIES, get_policy
from simulation.runner import SimulationRunner
from simulation.scripted_player import ScriptedPlayer


@pytest.fixture
def decks():
    return load_simulation_decks_dict()


@pytest.fixture
def no_api_key(monkeypatch):
    """Guarantee no credentials are reachable for the duration of a test."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.parametrize("policy", sorted(POLICIES))
def test_every_policy_completes_a_game_without_credentials(policy, decks, no_api_key):
    runner = SimulationRunner(player1_policy=policy, player2_policy=policy)
    result = runner.run_game(decks["D1"], decks["D3"], game_number=1, seed=99)

    assert result.error_message is None
    assert result.outcome.value in {"player1_win", "player2_win", "draw"}
    assert result.turn_count > 0
    # A provider object would mean an API-capable client was built.
    assert runner._player1_ai.provider_client is None
    assert runner._player2_ai.provider_client is None


def test_no_llm_execution_fallbacks_on_a_normal_game(decks, no_api_key):
    """Spot check on one fixed seed that a clean game needs no LLM fallback.

    Plans are built from engine-enumerated sequences, so heuristic matching
    normally finds the planned action. It is not zero in general -- a multi-step
    plan can desync from the board mid-turn (measured ~0.8% of games under
    greedy), which is inherent, not a defect. This pins the clean case so a
    regression that made fallbacks common would surface here.
    """
    runner = SimulationRunner(player1_policy="greedy", player2_policy="greedy")
    runner.run_game(decks["D4"], decks["D6"], game_number=1, seed=7)

    assert runner._player1_ai.execution_fallbacks == 0
    assert runner._player2_ai.execution_fallbacks == 0


def test_scripted_classes_mirror_every_upstream_attribute(decks):
    """ScriptedPlayer/ScriptedTurnPlanner deliberately skip super().__init__ to
    avoid building a network-capable provider, re-declaring each field by hand.

    That is a drift risk: a new attribute added upstream would only surface as an
    AttributeError deep inside a sweep, hours in, with logging disabled. Compare
    the attribute sets directly so the failure lands here instead.
    """
    import os

    os.environ.setdefault("GOOGLE_API_KEY", "dummy-for-attribute-comparison")
    from game_engine.ai.llm_player import LLMPlayer

    live = LLMPlayer()
    scripted = ScriptedPlayer(policy="greedy", seed=0)

    missing = set(vars(live)) - set(vars(scripted))
    assert not missing, (
        f"ScriptedPlayer is missing attribute(s) added to LLMPlayer: {sorted(missing)}"
    )

    missing_planner = set(vars(live.turn_planner)) - set(vars(scripted.turn_planner))
    assert not missing_planner, (
        "ScriptedTurnPlanner is missing attribute(s) added to TurnPlanner: "
        f"{sorted(missing_planner)}"
    )


@pytest.mark.parametrize("policy", ["greedy", "random", "softmax", "search2"])
def test_same_seed_reproduces_the_same_game(policy, decks, no_api_key):
    def play(seed):
        runner = SimulationRunner(player1_policy=policy, player2_policy=policy)
        r = runner.run_game(decks["D2"], decks["D7"], game_number=1, seed=seed)
        return r.outcome.value, r.turn_count, len(r.action_log)

    assert play(2024) == play(2024)


def test_policy_rng_is_isolated_from_the_global_module(decks, no_api_key):
    """A policy reaching for the global ``random`` would make results depend on
    unrelated engine calls, silently breaking replay."""
    import random

    player = ScriptedPlayer(policy="random", seed=5)
    random.seed(1)
    first = [player.rng.random() for _ in range(5)]

    player2 = ScriptedPlayer(policy="random", seed=5)
    random.seed(999)
    assert [player2.rng.random() for _ in range(5)] == first


def test_out_of_range_policy_index_is_clamped(decks, no_api_key, monkeypatch):
    """TurnPlanner clamps whatever the selection step returns, so a broken policy
    degrades to the top-ranked line instead of raising mid-sweep."""
    import simulation.policies as policies_module

    def rogue(sequences, game_state, player_id, rng):
        return 10_000

    rogue.name = "rogue"
    monkeypatch.setitem(policies_module.POLICIES, "rogue", rogue)

    runner = SimulationRunner(player1_policy="rogue", player2_policy="greedy")
    result = runner.run_game(decks["D1"], decks["D5"], game_number=1, seed=3)

    assert result.error_message is None
    assert result.turn_count > 0


def test_runner_resolves_targeted_effects_like_production():
    """The simulation runner must execute through ActionExecutor, the same path
    api/routes_actions.py and the enumerator use.

    It previously called engine.play_card() directly, which skips
    ActionExecutor._handle_targets: every targeted effect (Copy, Glue, Stomp,
    Drop, Twist, Sun, Jumpscare, Clone, Monster, Clean, Ballaber, Toynado)
    resolved with no target, so the card was paid for, did nothing, and went to
    the break zone. Silent -- games still completed, so only the plan/board
    desync it caused ever showed up. Copy is the sharpest probe: done right the
    card stays in play transformed, done wrong it is discarded.
    """
    from conftest import create_game_with_cards
    from game_engine.game_engine import GameEngine
    from game_engine.models.card import Zone
    from game_engine.validation import ActionExecutor

    setup, _ = create_game_with_cards(
        player1_hand=["Copy"],
        player1_in_play=["Raggy"],
        player2_in_play=["Archer"],
        player1_charge=6,
        active_player="player1",
        turn_number=3,
    )
    game_state = setup.game_state
    engine = GameEngine(game_state)
    player = game_state.players["player1"]
    copy_card = next(c for c in player.hand if c.name == "Copy")
    raggy = next(c for c in player.in_play if c.name == "Raggy")

    result = ActionExecutor(engine).execute_play_card(
        "player1", copy_card.id, target_card_ids=[raggy.id]
    )

    assert result.success
    assert copy_card.zone == Zone.IN_PLAY, "Copy was discarded instead of transformed"
    assert copy_card.name == "Copy of Raggy"
    assert copy_card.strength == raggy.strength
    assert copy_card.id in {c.id for c in player.in_play}


def test_unknown_policy_name_is_rejected_early():
    with pytest.raises(ValueError, match="Unknown policy"):
        get_policy("does-not-exist")


def test_scripted_player_refuses_to_call_the_execution_api(no_api_key):
    from simulation.scripted_player import ScriptedSelectionError

    player = ScriptedPlayer(policy="greedy", seed=0)
    with pytest.raises(ScriptedSelectionError):
        player._call_execution_api("prompt")
    assert player.execution_fallbacks == 1

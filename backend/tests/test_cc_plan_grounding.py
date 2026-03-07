"""
CC Plan Grounding Tests.

Covers two foundational bugs fixed together:

Bug 1 – cc_start wrong in plan
  LLMs (especially small-parameter ones like llama-3.1-8b-instant) frequently
  output cc_start=0 or a wrong value.  The planner now overrides cc_start with
  the actual player CC after parsing, so admin logs and any downstream logic
  are grounded in reality.

Bug 2 – plan/execution mismatch when planned action is not in valid_actions
  When a planned action (e.g., play Clean for 3 CC when player only has 2 CC)
  is not present in the valid_actions list, the old code fell back to the LLM
  execution API which would pick a *different* action and log it differently,
  making the plan shown in admin look completely unrelated to what was actually
  played.  The fix skips unavailable planned actions and advances to the next
  step instead of calling the LLM.

Test structure:
  - Unit tests (no LLM required): test the skip logic and cc_start grounding
    using mocks and direct method calls.
  - Live scenario tests (requires API key): turn-1 and turn-3 game states that
    reproduce the exact failures seen in production.

Run unit tests only:
    pytest tests/test_cc_plan_grounding.py -v -k "not Scenario"

Run all (needs API key):
    pytest tests/test_cc_plan_grounding.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import create_game_with_cards
from ai_test_support import has_valid_ai_api_key, build_turn_planner
from game_engine.ai.prompts.schemas import PlannedAction, TurnPlan


# ---------------------------------------------------------------------------
# Helpers shared across this module
# ---------------------------------------------------------------------------

def _make_planned_action(action_type: str, card_name: str = None, card_id: str = None) -> PlannedAction:
    return PlannedAction(
        action_type=action_type,
        card_id=card_id,
        card_name=card_name,
        target_ids=None,
        target_names=None,
        alternative_cost_id=None,
        cc_cost=0,
        cc_after=0,
        reasoning="test",
    )


def _make_valid_action(description: str) -> MagicMock:
    action = MagicMock()
    action.description = description
    return action


# ---------------------------------------------------------------------------
# Unit: _is_action_available
# ---------------------------------------------------------------------------

class TestIsActionAvailable:
    """Verify the loose availability check used to skip impossible plan steps."""

    @pytest.fixture
    def player(self):
        """Minimal LLMPlayerV3 instance (no real provider needed)."""
        from game_engine.ai.llm_player import LLMPlayerV3
        with patch("game_engine.ai.llm_player.LLMPlayerV3.__init__", return_value=None):
            p = LLMPlayerV3.__new__(LLMPlayerV3)
        return p

    def test_play_card_available_when_in_valid_actions(self, player):
        planned = _make_planned_action("play_card", card_name="Clean")
        valid = [_make_valid_action("Spend 3 CC to play Clean")]
        assert player._is_action_available(planned, valid) is True

    def test_play_card_unavailable_when_not_in_valid_actions(self, player):
        planned = _make_planned_action("play_card", card_name="Clean")
        valid = [_make_valid_action("Spend 1 CC to play Knight"), _make_valid_action("End turn")]
        assert player._is_action_available(planned, valid) is False

    def test_direct_attack_available(self, player):
        planned = _make_planned_action("direct_attack", card_name="Knight")
        valid = [_make_valid_action("Direct attack for 2 CC")]
        assert player._is_action_available(planned, valid) is True

    def test_direct_attack_unavailable_when_toys_remain(self, player):
        planned = _make_planned_action("direct_attack", card_name="Knight")
        valid = [_make_valid_action("Tussle Knight vs Umbruh"), _make_valid_action("End turn")]
        assert player._is_action_available(planned, valid) is False

    def test_tussle_available_any_target(self, player):
        planned = _make_planned_action("tussle", card_name="Knight")
        valid = [_make_valid_action("Tussle Knight vs Archer")]
        assert player._is_action_available(planned, valid) is True

    def test_end_turn_always_available(self, player):
        planned = _make_planned_action("end_turn")
        valid = [_make_valid_action("End turn")]
        assert player._is_action_available(planned, valid) is True

    def test_activate_ability_available(self, player):
        planned = _make_planned_action("activate_ability", card_name="Archer")
        valid = [_make_valid_action("Use Archer ability to remove 1 stamina")]
        assert player._is_action_available(planned, valid) is True


# ---------------------------------------------------------------------------
# Unit: _execute_planned_action skips impossible steps
# ---------------------------------------------------------------------------

class TestExecutionSkipsImpossibleActions:
    """
    When a planned action is not in valid_actions (e.g., card too expensive),
    execution should silently advance past it rather than calling the LLM.
    """

    @pytest.fixture
    def player_with_plan(self):
        """
        Build a minimal LLMPlayerV3 with a fake plan that has one unaffordable
        play_card (Clean) followed by end_turn.
        """
        from game_engine.ai.llm_player import LLMPlayerV3

        with patch("game_engine.ai.llm_player.LLMPlayerV3.__init__", return_value=None):
            p = LLMPlayerV3.__new__(LLMPlayerV3)

        # Inject minimal attributes checked by _execute_planned_action
        end_turn_action = _make_planned_action("end_turn")
        end_turn_action.cc_cost = 0
        clean_action = _make_planned_action("play_card", card_name="Clean")
        clean_action.cc_cost = 3

        plan = MagicMock(spec=TurnPlan)
        plan.action_sequence = [clean_action, end_turn_action]

        p._current_plan = plan
        p._plan_action_index = 0
        p._execution_log = []
        p._last_target_ids = None
        p._last_alternative_cost_id = None
        p._completed_actions = []

        return p

    def test_skips_clean_and_returns_end_turn(self, player_with_plan):
        """
        With only [end turn] in valid_actions, plan step 0 (play Clean) should
        be skipped; the returned action index should correspond to end_turn.
        """
        player = player_with_plan

        valid_actions = [_make_valid_action("End turn")]

        game_state = MagicMock()
        ai_player = MagicMock()
        ai_player.cc = 2
        game_state.players = {"p1": ai_player}

        result = player._execute_planned_action(valid_actions, game_state, "p1", None)

        # Should have advanced past Clean (index 0→1)
        assert player._plan_action_index == 2, "Plan index should be past end_turn after execution"
        # Result should be (0, ...) — index of end_turn in valid_actions
        assert result is not None
        action_idx, reasoning = result
        assert action_idx == 0
        assert "end_turn" in reasoning or "v3 Plan" in reasoning

    def test_plan_index_advanced_past_skipped_action(self, player_with_plan):
        """
        After skipping Clean, the internal plan index should have advanced so that
        a second call to select_action won't re-attempt Clean.
        """
        player = player_with_plan
        valid_actions = [_make_valid_action("End turn")]
        game_state = MagicMock()
        ai_player = MagicMock()
        ai_player.cc = 2
        game_state.players = {"p1": ai_player}

        player._execute_planned_action(valid_actions, game_state, "p1", None)

        assert player._plan_action_index >= 1


# ---------------------------------------------------------------------------
# Unit: cc_start is grounded to actual player CC after parsing
# ---------------------------------------------------------------------------

class TestCCStartGrounding:
    """
    After create_plan() returns, plan.cc_start must equal the player's real CC,
    regardless of what the LLM output.
    """

    def test_cc_start_overridden_after_parse(self):
        """
        Mock the LLM to return cc_start=0 in a game where the player has 2 CC.
        The returned plan must have cc_start=2.
        """
        from game_engine.ai.turn_planner import TurnPlanner

        setup, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=[],
            player2_in_play=[],
            player1_cc=2,
            active_player="player1",
            turn_number=1,
        )

        planner = build_turn_planner()

        # Inject a fake LLM response that has cc_start=0 (the bug)
        fake_response = """{
            "threat_assessment": "No threats",
            "resources_summary": "2 CC, Knight in hand",
            "sequences_considered": ["Play Knight"],
            "selected_strategy": "Play Knight",
            "action_sequence": [
                {
                    "action_type": "play_card",
                    "card_id": "fake-id",
                    "card_name": "Knight",
                    "cc_cost": 1,
                    "cc_after": 1,
                    "reasoning": "Play Knight"
                },
                {
                    "action_type": "end_turn",
                    "cc_cost": 0,
                    "cc_after": 1,
                    "reasoning": "End turn"
                }
            ],
            "cc_start": 0,
            "cc_after_plan": 1,
            "expected_cards_slept": 0,
            "cc_efficiency": "N/A",
            "plan_reasoning": "Play Knight and end turn."
        }"""

        with patch.object(planner, "_call_planning_api", return_value=fake_response):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None
        # The fix: cc_start must be corrected to actual player CC (2), not LLM's 0
        assert plan.cc_start == 2, (
            f"plan.cc_start should be 2 (actual player CC) but got {plan.cc_start}. "
            "LLM output cc_start=0 should have been overridden."
        )

    def test_negative_cc_after_clamped_to_zero(self):
        """
        LLM outputs cc_after=-1 for an action (e.g. wrong cost math).
        This must not crash with a Pydantic validation error — it should
        clamp to 0 and return a usable plan.
        """
        from game_engine.ai.turn_planner import TurnPlanner

        setup, _ = create_game_with_cards(
            player1_hand=["Knight"],
            player1_in_play=[],
            player2_in_play=[],
            player1_cc=2,
            active_player="player1",
            turn_number=1,
        )

        planner = build_turn_planner()

        # LLM outputs cc_after=-1 (wrong math) — this was causing a crash
        fake_response = """{
            "threat_assessment": "No threats",
            "resources_summary": "2 CC",
            "sequences_considered": ["Play Knight"],
            "selected_strategy": "Play Knight",
            "action_sequence": [
                {
                    "action_type": "play_card",
                    "card_id": "fake-id",
                    "card_name": "Knight",
                    "cc_cost": 3,
                    "cc_after": -1,
                    "reasoning": "Play Knight (wrong math)"
                },
                {
                    "action_type": "end_turn",
                    "cc_cost": 0,
                    "cc_after": -1,
                    "reasoning": "End turn"
                }
            ],
            "cc_start": 2,
            "cc_after_plan": -1,
            "expected_cards_slept": 0,
            "cc_efficiency": "N/A",
            "plan_reasoning": "Test."
        }"""

        # Must not raise — previously crashed with Pydantic ValidationError
        with patch.object(planner, "_call_planning_api", return_value=fake_response):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None, "Plan should be returned despite LLM's wrong cc_after=-1"
        for action in plan.action_sequence:
            assert action.cc_after >= 0, (
                f"cc_after must be >= 0 after clamping, got {action.cc_after} for {action.action_type}"
            )


# ---------------------------------------------------------------------------
# Live LLM scenario tests (skipped when no valid API key)
# ---------------------------------------------------------------------------

_SKIP_LLM = pytest.mark.skipif(
    not has_valid_ai_api_key(),
    reason="Valid API key not set - skipping live LLM tests",
)


def _validate_no_negative_cc(plan) -> list[str]:
    """Return list of error messages for any action that would go below 0 CC."""
    CC_GAINS = {"Surge": 1, "Rush": 2, "HLK": 1}
    running_cc = plan.cc_start
    errors = []
    for i, action in enumerate(plan.action_sequence, 1):
        if action.action_type == "end_turn":
            continue
        gain = CC_GAINS.get(action.card_name or "", 0)
        after = running_cc - action.cc_cost + gain
        if after < 0:
            errors.append(
                f"Action {i} ({action.action_type} {action.card_name or ''}): "
                f"{running_cc} - {action.cc_cost} + {gain} = {after} (negative!)"
            )
        running_cc = max(0, after)
    return errors


@_SKIP_LLM
class TestTurn1Clean3CCUnaffordable:
    """
    Turn 1: player has 2 CC and Clean (costs 3) is in hand.
    The plan must NOT try to play Clean — it would go negative CC.
    """

    @pytest.fixture
    def turn_planner(self):
        return build_turn_planner()

    def test_plan_does_not_include_unaffordable_clean(self, turn_planner):
        setup, _ = create_game_with_cards(
            player1_hand=["Clean", "Knight"],
            player1_in_play=[],
            player2_in_play=[],
            player1_cc=2,
            active_player="player1",
            turn_number=1,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None

        print(f"\nCC start: {plan.cc_start}")
        for i, a in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {a.action_type} {a.card_name or ''} ({a.cc_cost} CC → {a.cc_after})")

        # cc_start must be the actual player CC
        assert plan.cc_start == 2, f"cc_start should be 2, got {plan.cc_start}"

        # Plan must not go negative
        errors = _validate_no_negative_cc(plan)
        assert len(errors) == 0, f"Plan has impossible CC math:\n" + "\n".join(errors)

        # Clean must not appear in the plan (unaffordable: costs 3, only 2 CC)
        clean_plays = [
            a for a in plan.action_sequence
            if a.action_type == "play_card" and a.card_name == "Clean"
        ]
        assert len(clean_plays) == 0, (
            "Plan included play_card Clean despite only having 2 CC (Clean costs 3). "
            "This would fail at execution and cause plan/log mismatch."
        )


@_SKIP_LLM
class TestTurn3Clean5CCAffordable:
    """
    Turn 3 (P1): player has 5 CC (4 CC gain + 1 CC carryover) and Clean in hand.
    Clean costs 3 CC → should be affordable and appear in the plan if it's the
    best move when opponent has toys.
    """

    @pytest.fixture
    def turn_planner(self):
        return build_turn_planner()

    def test_cc_start_reflects_actual_cc(self, turn_planner):
        """cc_start must equal 5 regardless of what the LLM reports."""
        setup, _ = create_game_with_cards(
            player1_hand=["Clean", "Raggy"],
            player1_in_play=[],
            player2_in_play=["Knight", "Umbruh"],
            player1_cc=5,
            player2_cc=4,
            active_player="player1",
            turn_number=3,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None

        print(f"\nCC start: {plan.cc_start}")
        for i, a in enumerate(plan.action_sequence, 1):
            print(f"  {i}. {a.action_type} {a.card_name or ''} ({a.cc_cost} CC → {a.cc_after})")

        assert plan.cc_start == 5, f"cc_start should be 5 (actual player CC), got {plan.cc_start}"

    def test_plan_cc_never_goes_negative(self, turn_planner):
        """Even with multiple actions, CC must never go below zero at any step."""
        setup, _ = create_game_with_cards(
            player1_hand=["Clean", "Raggy"],
            player1_in_play=[],
            player2_in_play=["Knight", "Umbruh"],
            player1_cc=5,
            player2_cc=4,
            active_player="player1",
            turn_number=3,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None

        errors = _validate_no_negative_cc(plan)
        assert len(errors) == 0, (
            f"Plan has CC math errors after cc_start grounding:\n" + "\n".join(errors)
        )

    def test_clean_is_playable_when_player_can_afford_it(self, turn_planner):
        """
        With 5 CC and opponent toys in play, Clean (3 CC board wipe) is the
        correct efficient move.  The plan should include it.
        """
        setup, _ = create_game_with_cards(
            player1_hand=["Clean", "Raggy"],
            player1_in_play=[],
            player2_in_play=["Knight", "Umbruh"],
            player1_cc=5,
            player2_cc=4,
            active_player="player1",
            turn_number=3,
        )

        plan = turn_planner.create_plan(setup.game_state, "player1", setup.engine)
        assert plan is not None

        clean_plays = [
            a for a in plan.action_sequence
            if a.action_type == "play_card" and a.card_name == "Clean"
        ]
        assert len(clean_plays) == 1, (
            "Expected plan to include play_card Clean (5 CC available, opponent has 2 toys). "
            f"Actions: {[(a.action_type, a.card_name) for a in plan.action_sequence]}"
        )


# ---------------------------------------------------------------------------
# Unit: _parse_plan robustness — the *actual* failure modes for
#       "AI failed to select action, ended turn"
# ---------------------------------------------------------------------------
# These tests directly replicate the production crashes that caused
# turn 1 to always fail.  Previously each scenario threw an exception
# inside _parse_plan which propagated through create_plan → None, and the
# v2 fallback LLM call also 429'd on Groq, leaving select_action returning
# None entirely.

class TestParsePlanRobustness:
    """_parse_plan must never throw, regardless of malformed LLM output."""

    @pytest.fixture
    def planner(self):
        return build_turn_planner()

    def _fake_response(self, action_sequence_json: str) -> str:
        return (
            '{"threat_assessment":"","resources_summary":"",'
            '"sequences_considered":[],"selected_strategy":"",'
            f'"action_sequence":{action_sequence_json},'
            '"cc_start":2,"cc_after_plan":0,"expected_cards_slept":0,'
            '"cc_efficiency":"N/A","plan_reasoning":""}'
        )

    def test_invalid_action_type_does_not_crash(self, planner):
        """
        LLM outputs action_type="play" (not a valid Literal).
        Previously caused Pydantic ValidationError → plan returned None
        → 'AI failed to select action, ended turn'.
        """
        fake = self._fake_response(
            '[{"action_type":"play","card_name":"Knight",'
            '"cc_cost":1,"cc_after":1,"reasoning":"play knight"}]'
        )
        setup, _ = create_game_with_cards(
            player1_hand=["Knight"], player1_cc=2,
            active_player="player1", turn_number=1,
        )
        with patch.object(planner, "_call_planning_api", return_value=fake):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None, (
            "create_plan must not return None when LLM outputs invalid action_type='play'"
        )
        # The invalid action should have been silently coerced to end_turn
        for action in plan.action_sequence:
            assert action.action_type in {
                "play_card", "tussle", "activate_ability", "direct_attack", "end_turn"
            }, f"Unexpected action_type after coercion: {action.action_type!r}"

    def test_action_type_attack_coerced_to_end_turn(self, planner):
        """LLM outputs 'attack' which is also not a valid Literal."""
        fake = self._fake_response(
            '[{"action_type":"attack","card_name":"Knight",'
            '"cc_cost":2,"cc_after":0,"reasoning":"attack"},'
            '{"action_type":"end_turn","cc_cost":0,"cc_after":0,"reasoning":"done"}]'
        )
        setup, _ = create_game_with_cards(
            player1_hand=["Knight"], player1_cc=2,
            active_player="player1", turn_number=1,
        )
        with patch.object(planner, "_call_planning_api", return_value=fake):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None
        for action in plan.action_sequence:
            assert action.action_type in {
                "play_card", "tussle", "activate_ability", "direct_attack", "end_turn"
            }

    def test_null_cc_cost_does_not_crash(self, planner):
        """
        LLM outputs "cc_cost": null  — JSON null becomes Python None.
        Previously max(0, None) raised TypeError → plan returned None
        → 'AI failed to select action, ended turn'.
        """
        fake = self._fake_response(
            '[{"action_type":"play_card","card_name":"Knight",'
            '"cc_cost":null,"cc_after":null,"reasoning":"play"},'
            '{"action_type":"end_turn","cc_cost":0,"cc_after":0,"reasoning":"done"}]'
        )
        setup, _ = create_game_with_cards(
            player1_hand=["Knight"], player1_cc=2,
            active_player="player1", turn_number=1,
        )
        with patch.object(planner, "_call_planning_api", return_value=fake):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None, (
            "create_plan must not return None when LLM outputs 'cc_cost': null"
        )
        for action in plan.action_sequence:
            assert action.cc_cost >= 0
            assert action.cc_after >= 0

    def test_null_reasoning_does_not_crash(self, planner):
        """LLM outputs "reasoning": null — must not fail Pydantic's required str field."""
        fake = self._fake_response(
            '[{"action_type":"play_card","card_name":"Knight",'
            '"cc_cost":1,"cc_after":1,"reasoning":null},'
            '{"action_type":"end_turn","cc_cost":0,"cc_after":1,"reasoning":null}]'
        )
        setup, _ = create_game_with_cards(
            player1_hand=["Knight"], player1_cc=2,
            active_player="player1", turn_number=1,
        )
        with patch.object(planner, "_call_planning_api", return_value=fake):
            plan = planner.create_plan(setup.game_state, "player1", setup.engine)

        assert plan is not None
        for action in plan.action_sequence:
            assert isinstance(action.reasoning, str) and len(action.reasoning) > 0


# ---------------------------------------------------------------------------
# Unit: skip-all-actions path never returns None
# ---------------------------------------------------------------------------

class TestSkipAllActionsNeverReturnsNone:
    """
    If every non-end_turn action in a plan is unavailable (all skipped),
    execution must still return an (index, reason) for end_turn — not None.
    Returning None here propagated directly to 'AI failed to select action'.
    """

    def _build_player_with_plan(self, action_types: list[str]):
        """Construct a minimal LLMPlayerV3 with a plan from the given action_types."""
        from game_engine.ai.llm_player import LLMPlayerV3

        with patch("game_engine.ai.llm_player.LLMPlayerV3.__init__", return_value=None):
            p = LLMPlayerV3.__new__(LLMPlayerV3)

        actions = []
        for at in action_types:
            a = _make_planned_action(at, card_name="Anything" if at != "end_turn" else None)
            a.cc_cost = 0
            actions.append(a)

        plan = MagicMock(spec=TurnPlan)
        plan.action_sequence = actions
        p._current_plan = plan
        p._plan_action_index = 0
        p._execution_log = []
        p._last_target_ids = None
        p._last_alternative_cost_id = None
        p._completed_actions = []
        return p

    def test_all_card_plays_skipped_returns_end_turn(self):
        """
        Plan has 3 play_card actions (all unavailable) + end_turn.
        Must return the end_turn index, not None.
        """
        player = self._build_player_with_plan(
            ["play_card", "play_card", "play_card", "end_turn"]
        )
        # Only end_turn is valid
        valid = [_make_valid_action("End turn")]
        game_state = MagicMock()
        game_state.players = {"p1": MagicMock(cc=0)}

        result = player._execute_planned_action(valid, game_state, "p1", None)

        assert result is not None, (
            "_execute_planned_action must not return None when all play_card steps "
            "are unavailable — it should fall through to end_turn"
        )
        action_idx, reasoning = result
        assert action_idx == 0

    def test_all_tussles_skipped_returns_end_turn(self):
        """Plan has 2 tussles (no valid tussle targets) + end_turn."""
        player = self._build_player_with_plan(["tussle", "tussle", "end_turn"])
        valid = [_make_valid_action("End turn")]
        game_state = MagicMock()
        game_state.players = {"p1": MagicMock(cc=0)}

        result = player._execute_planned_action(valid, game_state, "p1", None)

        assert result is not None, "Should fall through to end_turn when tussles unavailable"
        action_idx, _ = result
        assert action_idx == 0


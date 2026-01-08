import os

from game_engine.ai.llm_player import LLMPlayerV3


class _DummyPlannedAction:
    def __init__(self) -> None:
        self.action_type = "play_card"
        self.card_name = "Archer"
        self.target_names = ["Knight"]
        self.cc_cost = 1
        self.reasoning = "test"


class _DummyPlan:
    def __init__(self) -> None:
        self.selected_strategy = "test-strategy"
        self.action_sequence = [_DummyPlannedAction()]
        self.cc_start = 4
        self.cc_after_plan = 3
        self.expected_cards_slept = 0
        self.cc_efficiency = "N/A"


class _DummyTurnPlanner:
    def get_last_plan_info(self) -> dict:
        return {
            "prompt": "REQUEST1_PROMPT",
            "response": "REQUEST1_RESPONSE",
            "v4_request1_prompt": "REQUEST1_PROMPT",
            "v4_request1_response": "REQUEST1_RESPONSE",
            "v4_request2_prompt": "REQUEST2_PROMPT",
            "v4_request2_response": "REQUEST2_RESPONSE",
            "v4_metrics": {"v4_success": 1},
        }


def test_llm_player_v3_last_decision_info_includes_v4_request2() -> None:
    os.environ["AI_VERSION"] = "4"

    # Avoid running the real __init__ (Gemini client). We only need the logger payload.
    player = object.__new__(LLMPlayerV3)

    # Base (v2) decision info fields
    player._last_prompt = None
    player._last_response = None
    player._last_action_number = None
    player._last_reasoning = None
    player.model_name = "gemini-2.5-flash-lite"

    # v3/v4 plan fields
    player._current_plan = _DummyPlan()
    player._plan_action_index = 0
    player._execution_log = []
    player.turn_planner = _DummyTurnPlanner()

    info = player.get_last_decision_info()
    assert "v3_plan" in info

    v3_plan = info["v3_plan"]
    assert v3_plan["planning_prompt"] == "REQUEST1_PROMPT"
    assert v3_plan["planning_response"] == "REQUEST1_RESPONSE"
    assert v3_plan["v4_request2_prompt"] == "REQUEST2_PROMPT"
    assert v3_plan["v4_request2_response"] == "REQUEST2_RESPONSE"

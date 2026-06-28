"""
Tests for Batch 2 cards: Clone, Glue, Stomp.

Clone reuses Copy's copy_card effect but at a flat cost (regression coverage
for a latent bug where the variable-cost dispatch was keyed on effect type
alone, which would have silently hijacked Clone's flat cost).

Glue (fix:1) and Stomp (break_target:1) introduce variable cost - the
play cost equals the effective cost of whichever card is targeted - which
generalizes a mechanic that previously only existed for Copy. These tests
also cover the generalized ActionValidator affordability filter and the
ActionExecutor cost-reporting fix (cost must be computed after the target is
resolved, not before).
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from conftest import create_game_with_cards
from game_engine.models.game_state import Phase
from game_engine.validation.action_validator import ActionValidator
from game_engine.validation.action_executor import ActionExecutor


class TestCloneFlatCost:
    """Clone has the same copy_card effect as Copy, but a fixed cost of 2."""

    def test_clone_cost_is_flat_regardless_of_cheap_target(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Clone"],
            player1_in_play=["Knight"],  # Knight costs 1
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        clone = cards["p1_hand_Clone"]
        knight = cards["p1_inplay_Knight"]
        cost = setup.engine.calculate_card_cost(clone, setup.player1, target_id=knight.id)
        assert cost == 2, f"Clone should always cost 2, got {cost}"

    def test_clone_cost_is_flat_regardless_of_expensive_target(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Clone"],
            player1_in_play=["Wizard"],  # Wizard costs 2
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        clone = cards["p1_hand_Clone"]
        wizard = cards["p1_inplay_Wizard"]
        cost = setup.engine.calculate_card_cost(clone, setup.player1, target_id=wizard.id)
        assert cost == 2, f"Clone should always cost 2 even when targeting a costlier toy, got {cost}"

    def test_clone_cost_with_no_cards_in_play(self):
        """Clone's flat cost shouldn't fall back to 0 just because there's nothing to copy."""
        setup, cards = create_game_with_cards(
            player1_hand=["Clone"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        clone = cards["p1_hand_Clone"]
        cost = setup.engine.calculate_card_cost(clone, setup.player1)
        assert cost == 2


class TestGlueVariableCost:
    """Glue (fix:1) costs the effective cost of the broken card it targets."""

    def test_glue_cost_equals_cheap_target_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Surge"],  # Surge costs 0
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        surge = cards["p1_break_Surge"]
        cost = setup.engine.calculate_card_cost(glue, setup.player1, target_id=surge.id)
        assert cost == 0

    def test_glue_cost_equals_expensive_target_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Ka"],  # Ka costs 2
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        ka = cards["p1_break_Ka"]
        cost = setup.engine.calculate_card_cost(glue, setup.player1, target_id=ka.id)
        assert cost == 2

    def test_glue_uses_targets_effective_cost_not_base_cost(self):
        """Targeting Dream (base cost 4) while it sits among other broken cards
        should use Dream's reduced effective cost, mirroring Copy's behavior."""
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Dream", "Surge"],  # 2 cards in break zone -> Dream costs 4-2=2
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        dream = cards["p1_break_Dream"]
        cost = setup.engine.calculate_card_cost(glue, setup.player1, target_id=dream.id)
        assert cost == 2, f"Expected Dream's effective cost (2), got {cost}"

    def test_glue_cannot_target_opponents_break_zone(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player2_break=["Ka"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        from game_engine.rules.effects.effect_registry import EffectRegistry
        effect = next(e for e in EffectRegistry.get_effects(glue) if e.requires_targets())
        valid_targets = effect.get_valid_targets(setup.game_state, player=setup.player1)
        assert valid_targets == [], "Glue must not be able to target the opponent's Break Zone"

    def test_glue_no_target_falls_back_to_cheapest_broken_card(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Ka", "Surge"],  # Ka costs 2, Surge costs 0
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        cost = setup.engine.calculate_card_cost(glue, setup.player1)
        assert cost == 0, f"With no target chosen, should conservatively estimate the cheapest (0), got {cost}"

    def test_glue_play_through_engine_unbreaks_target_and_deducts_correct_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Ka", "Surge"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        glue = cards["p1_hand_Glue"]
        ka = cards["p1_break_Ka"]

        success = setup.engine.play_card(setup.player1, glue, target_ids=[ka.id])

        assert success
        assert ka in setup.player1.hand
        assert ka not in setup.player1.break_zone
        assert setup.player1.charge == 8, f"Should have spent Ka's cost (2), got charge={setup.player1.charge}"


class TestStompVariableCost:
    """Stomp (break_target:1) costs the effective cost of the in-play card it targets."""

    def test_stomp_cost_equals_opponents_target_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player2_in_play=["Ka"],  # Ka costs 2
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        stomp = cards["p1_hand_Stomp"]
        ka = cards["p2_inplay_Ka"]
        cost = setup.engine.calculate_card_cost(stomp, setup.player1, target_id=ka.id)
        assert cost == 2

    def test_stomp_cost_equals_own_target_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player1_in_play=["Knight"],  # Knight costs 1
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        stomp = cards["p1_hand_Stomp"]
        knight = cards["p1_inplay_Knight"]
        cost = setup.engine.calculate_card_cost(stomp, setup.player1, target_id=knight.id)
        assert cost == 1

    def test_stomp_no_target_falls_back_to_cheapest_in_play_card(self):
        setup, cards = create_game_with_cards(
            player1_in_play=["Knight"],  # cost 1
            player2_in_play=["Ka"],      # cost 2
            player1_hand=["Stomp"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        stomp = cards["p1_hand_Stomp"]
        cost = setup.engine.calculate_card_cost(stomp, setup.player1)
        assert cost == 1, f"Should conservatively estimate the cheapest in-play card (1), got {cost}"

    def test_stomp_excludes_protected_targets(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player2_in_play=["Beary"],  # opponent_immunity
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        stomp = cards["p1_hand_Stomp"]
        from game_engine.rules.effects.effect_registry import EffectRegistry
        effect = next(e for e in EffectRegistry.get_effects(stomp) if e.requires_targets())
        valid_targets = effect.get_valid_targets(setup.game_state, player=setup.player1)
        assert valid_targets == [], "Beary's opponent_immunity should block Stomp from targeting it"

    def test_stomp_play_through_engine_breaks_target_and_deducts_correct_cost(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player2_in_play=["Ka"],
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        stomp = cards["p1_hand_Stomp"]
        ka = cards["p2_inplay_Ka"]

        success = setup.engine.play_card(setup.player1, stomp, target_ids=[ka.id])

        assert success
        assert ka in setup.player2.break_zone
        assert ka not in setup.player2.in_play
        assert setup.player1.charge == 8, f"Should have spent Ka's cost (2), got charge={setup.player1.charge}"


class TestActionValidatorAffordabilityFilter:
    """Glue/Stomp should filter their target menu to affordable targets, like Copy does."""

    def test_glue_target_options_exclude_unaffordable_breaking_cards(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Glue"],
            player1_break=["Surge", "Ka"],  # Surge costs 0, Ka costs 2
            active_player="player1",
            turn_number=1,
            player1_charge=1,
        )
        glue = cards["p1_hand_Glue"]
        surge = cards["p1_break_Surge"]
        ka = cards["p1_break_Ka"]

        validator = ActionValidator(setup.engine)
        actions = validator.get_valid_actions(setup.player1.player_id)
        glue_actions = [a for a in actions if a.card_id == glue.id]

        assert len(glue_actions) == 1
        assert glue_actions[0].target_options == [surge.id], (
            f"Only the affordable target (Surge) should be offered, got {glue_actions[0].target_options}"
        )
        assert ka.id not in (glue_actions[0].target_options or [])

    def test_stomp_target_options_exclude_unaffordable_in_play_cards(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player1_in_play=["Knight"],  # cost 1
            player2_in_play=["Ka"],      # cost 2
            active_player="player1",
            turn_number=1,
            player1_charge=1,
        )
        stomp = cards["p1_hand_Stomp"]
        knight = cards["p1_inplay_Knight"]
        ka = cards["p2_inplay_Ka"]

        validator = ActionValidator(setup.engine)
        actions = validator.get_valid_actions(setup.player1.player_id)
        stomp_actions = [a for a in actions if a.card_id == stomp.id]

        assert len(stomp_actions) == 1
        assert stomp_actions[0].target_options == [knight.id]
        assert ka.id not in (stomp_actions[0].target_options or [])


class TestActionExecutorCostReporting:
    """
    Regression coverage for a pre-existing bug: cost used to be computed
    before the target was resolved, so the executor's reported cost (and
    description) could mismatch the Charge actually deducted whenever the chosen
    target wasn't the cheapest available one.
    """

    def test_copy_reports_actual_target_cost_not_cheapest_estimate(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Copy"],
            player1_in_play=["Knight", "Ka"],  # Knight costs 1 (cheapest), Ka costs 2
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        copy_card = cards["p1_hand_Copy"]
        ka = cards["p1_inplay_Ka"]

        executor = ActionExecutor(setup.engine)
        result = executor.execute_play_card(
            player_id=setup.player1.player_id,
            card_id=copy_card.id,
            target_card_id=ka.id,
        )

        assert result.success
        assert result.cost == 2, f"Should report Ka's actual cost (2), not the cheaper Knight's, got {result.cost}"
        assert setup.player1.charge == 8

    def test_stomp_reports_actual_target_cost_not_cheapest_estimate(self):
        setup, cards = create_game_with_cards(
            player1_hand=["Stomp"],
            player1_in_play=["Knight"],  # cost 1 (cheapest)
            player2_in_play=["Ka"],      # cost 2 (the actual target)
            active_player="player1",
            turn_number=1,
            player1_charge=10,
        )
        setup.game_state.phase = Phase.MAIN
        stomp = cards["p1_hand_Stomp"]
        ka = cards["p2_inplay_Ka"]

        executor = ActionExecutor(setup.engine)
        result = executor.execute_play_card(
            player_id=setup.player1.player_id,
            card_id=stomp.id,
            target_card_id=ka.id,
        )

        assert result.success
        assert result.cost == 2, f"Should report Ka's actual cost (2), not Knight's cheaper cost, got {result.cost}"
        assert setup.player1.charge == 8

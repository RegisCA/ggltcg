"""
Batch 4: "When played" Toys — MA14, Sock Serpent, Sir Scares a lot, Candy Golem,
Laundry Lad.

Rules (Sully, via Régis):
- A Toy's "When played" effect resolves when the Toy enters play from its
  controller's hand. Choosing a target is always optional.
- MA14 fixes from its controller's Break Zone; Sock Serpent and Sir Scares a lot
  may only pick a card the opponent *controls* (a card they took with Twist counts).
- Laundry Lad sets the opponent's Charge to 0. Immunity (Beary, Sock Sorcerer,
  Bubble Blocker) covers cards, not Charge, so it does not stop it.
- Copy/Clone becoming a copy of one of these Toys does not trigger the effect —
  the Copy card was played, not the copied card. Neither does Twist.

Most plays go through ActionExecutor (the path the API and the AI use), so target
validation and the play-by-play description are exercised too. Odd turns =
player1, even turns = player2.
"""

import pytest

from conftest import create_game_with_cards, steal_card
from game_engine.ai.card_metadata import CHARGE_GAIN_ON_PLAY
from game_engine.ai.enumerator import _expand_action
from game_engine.models.card import Zone
from game_engine.rules.effects.action_effects import BreakTargetEffect
from game_engine.rules.effects.effect_registry import EffectRegistry
from game_engine.validation.action_executor import ActionExecutor
from game_engine.validation.action_validator import ActionValidator


def _play(setup, player, card, targets=()):
    return ActionExecutor(setup.engine).execute_play_card(
        player.player_id, card.id, target_card_ids=[t.id for t in targets] or None
    )


def _play_action(setup, player, card):
    actions = ActionValidator(setup.engine).get_valid_actions(player.player_id)
    matches = [a for a in actions if a.action_type == "play_card" and a.card_id == card.id]
    assert matches, f"{card.name} should be playable"
    return matches[0]


def _p1_game(**kwargs):
    kwargs.setdefault("active_player", "player1")
    kwargs.setdefault("turn_number", 3)
    return create_game_with_cards(**kwargs)


# ============================================================================
# CSV / parsing
# ============================================================================

class TestCardData:
    @pytest.mark.parametrize("name", ["MA14", "Sock Serpent", "Sir Scares a lot", "Candy Golem", "Laundry Lad"])
    def test_cards_are_toys(self, name):
        setup, cards = _p1_game(player1_hand=[name])
        assert cards[f"p1_hand_{name}"].is_toy()

    def test_candy_golem_feeds_the_ai_charge_table(self):
        assert CHARGE_GAIN_ON_PLAY["Candy Golem"] == 4


# ============================================================================
# MA14 — "When played, you may fix 1 of your cards."
# ============================================================================

class TestMA14:
    def test_fixes_chosen_card_from_own_break_zone(self):
        setup, cards = _p1_game(player1_hand=["MA14"], player1_break=["Knight", "Ka"], player1_charge=4)
        ma14, knight = cards["p1_hand_MA14"], cards["p1_break_Knight"]

        result = _play(setup, setup.player1, ma14, [knight])

        assert result.success
        assert ma14.zone == Zone.IN_PLAY
        assert knight in setup.player1.hand
        assert cards["p1_break_Ka"] in setup.player1.break_zone
        assert setup.player1.charge == 2
        assert "fixed Knight" in result.description

    def test_targets_are_own_break_zone_only_and_optional(self):
        setup, cards = _p1_game(player1_hand=["MA14"], player1_break=["Knight"], player2_break=["Ka"])
        action = _play_action(setup, setup.player1, cards["p1_hand_MA14"])
        assert action.target_options == [cards["p1_break_Knight"].id]
        assert action.min_targets == 0

    def test_may_decline_the_fix(self):
        setup, cards = _p1_game(player1_hand=["MA14"], player1_break=["Knight"])
        assert _play(setup, setup.player1, cards["p1_hand_MA14"]).success
        assert cards["p1_break_Knight"] in setup.player1.break_zone

    def test_playable_with_empty_break_zone(self):
        setup, cards = _p1_game(player1_hand=["MA14"])
        action = _play_action(setup, setup.player1, cards["p1_hand_MA14"])
        assert not action.target_options
        assert _play(setup, setup.player1, cards["p1_hand_MA14"]).success


# ============================================================================
# Sock Serpent — "When played, you may break a card your opponent has in play."
# ============================================================================

class TestSockSerpent:
    def test_breaks_opponent_card(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Knight"], player1_charge=5)
        serpent, knight = cards["p1_hand_Sock Serpent"], cards["p2_inplay_Knight"]

        result = _play(setup, setup.player1, serpent, [knight])

        assert result.success
        assert serpent.zone == Zone.IN_PLAY
        assert knight in setup.player2.break_zone
        assert setup.player1.charge == 2
        assert "broke Knight" in result.description

    def test_own_cards_are_not_targets(self):
        setup, cards = _p1_game(
            player1_hand=["Sock Serpent"], player1_in_play=["Ka"], player2_in_play=["Knight"]
        )
        action = _play_action(setup, setup.player1, cards["p1_hand_Sock Serpent"])
        assert action.target_options == [cards["p2_inplay_Knight"].id]
        assert action.min_targets == 0

    def test_executor_rejects_own_card_as_target(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player1_in_play=["Ka"])
        with pytest.raises(ValueError, match="Invalid target"):
            _play(setup, setup.player1, cards["p1_hand_Sock Serpent"], [cards["p1_inplay_Ka"]])
        assert cards["p1_inplay_Ka"].zone == Zone.IN_PLAY

    def test_engine_rechecks_scope_at_resolution(self):
        """A direct engine call (no executor validation) still can't break your own card."""
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player1_in_play=["Ka"])
        ka = cards["p1_inplay_Ka"]
        assert setup.engine.play_card(setup.player1, cards["p1_hand_Sock Serpent"], target_ids=[ka.id])
        assert ka.zone == Zone.IN_PLAY

    def test_may_decline_the_break(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Knight"])
        assert _play(setup, setup.player1, cards["p1_hand_Sock Serpent"]).success
        assert cards["p2_inplay_Knight"].zone == Zone.IN_PLAY

    def test_beary_cannot_be_targeted(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Beary", "Knight"])
        action = _play_action(setup, setup.player1, cards["p1_hand_Sock Serpent"])
        assert action.target_options == [cards["p2_inplay_Knight"].id]

    @pytest.mark.parametrize("protector", ["Sock Sorcerer", "Bubble Blocker"])
    def test_team_immunity_leaves_a_vanilla_body(self, protector):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=[protector, "Knight"])
        serpent = cards["p1_hand_Sock Serpent"]
        action = _play_action(setup, setup.player1, serpent)
        assert not action.target_options
        assert _play(setup, setup.player1, serpent).success
        assert serpent.zone == Zone.IN_PLAY

    def test_card_opponent_stole_is_a_target_and_goes_back_to_owner(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player1_in_play=["Knight"])
        knight = cards["p1_inplay_Knight"]
        steal_card(setup.game_state, knight, "player2")

        assert _play_action(setup, setup.player1, cards["p1_hand_Sock Serpent"]).target_options == [knight.id]
        assert _play(setup, setup.player1, cards["p1_hand_Sock Serpent"], [knight]).success
        assert knight in setup.player1.break_zone
        assert knight not in setup.player2.in_play

    def test_card_you_stole_is_not_a_target(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Knight"])
        steal_card(setup.game_state, cards["p2_inplay_Knight"], "player1")
        assert not _play_action(setup, setup.player1, cards["p1_hand_Sock Serpent"]).target_options

    def test_break_fires_when_broken_trigger(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Umbruh"], player2_charge=2)
        _play(setup, setup.player1, cards["p1_hand_Sock Serpent"], [cards["p2_inplay_Umbruh"]])
        assert setup.player2.charge == 3

    def test_hind_leg_kicker_still_triggers(self):
        setup, cards = _p1_game(
            player1_hand=["Sock Serpent"], player1_in_play=["Hind Leg Kicker"],
            player2_in_play=["Knight"], player1_charge=5,
        )
        _play(setup, setup.player1, cards["p1_hand_Sock Serpent"], [cards["p2_inplay_Knight"]])
        assert setup.player1.charge == 3  # 5 - 3 + 1

    def test_enumerator_branches_on_no_target(self):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Knight"])
        action = _play_action(setup, setup.player1, cards["p1_hand_Sock Serpent"])
        combos = [s["target_ids"] for s in _expand_action(action, setup.game_state)]
        assert combos == [(), (cards["p2_inplay_Knight"].id,)]


# ============================================================================
# Sir Scares a lot — "When played, you may put a card your opponent has in play
# into their owner's hand."
# ============================================================================

class TestSirScaresALot:
    def test_returns_opponent_card_to_hand(self):
        setup, cards = _p1_game(player1_hand=["Sir Scares a lot"], player2_in_play=["Ka"], player1_charge=3)
        sir, ka = cards["p1_hand_Sir Scares a lot"], cards["p2_inplay_Ka"]

        result = _play(setup, setup.player1, sir, [ka])

        assert result.success
        assert sir.zone == Zone.IN_PLAY
        assert ka in setup.player2.hand
        assert ka.zone == Zone.HAND
        assert setup.player1.charge == 2
        assert "returned Ka to hand" in result.description

    def test_own_cards_are_not_targets(self):
        setup, cards = _p1_game(
            player1_hand=["Sir Scares a lot"], player1_in_play=["Knight"], player2_in_play=["Ka"]
        )
        action = _play_action(setup, setup.player1, cards["p1_hand_Sir Scares a lot"])
        assert action.target_options == [cards["p2_inplay_Ka"].id]
        assert action.min_targets == 0

    def test_card_opponent_stole_returns_to_owner_hand(self):
        setup, cards = _p1_game(player1_hand=["Sir Scares a lot"], player1_in_play=["Knight"])
        knight = cards["p1_inplay_Knight"]
        steal_card(setup.game_state, knight, "player2")

        assert _play(setup, setup.player1, cards["p1_hand_Sir Scares a lot"], [knight]).success
        assert knight in setup.player1.hand
        assert knight not in setup.player2.in_play

    def test_playable_with_no_opponent_cards(self):
        setup, cards = _p1_game(player1_hand=["Sir Scares a lot"])
        assert _play(setup, setup.player1, cards["p1_hand_Sir Scares a lot"]).success

    def test_beary_cannot_be_targeted(self):
        setup, cards = _p1_game(player1_hand=["Sir Scares a lot"], player2_in_play=["Beary"])
        assert not _play_action(setup, setup.player1, cards["p1_hand_Sir Scares a lot"]).target_options


# ============================================================================
# Candy Golem — "When played, gain 4 Charge."
# ============================================================================

class TestCandyGolem:
    def test_gains_4_after_paying(self):
        setup, cards = _p1_game(player1_hand=["Candy Golem"], player1_charge=6)
        assert _play(setup, setup.player1, cards["p1_hand_Candy Golem"]).success
        assert cards["p1_hand_Candy Golem"].zone == Zone.IN_PLAY
        assert setup.player1.charge == 4

    def test_not_playable_below_cost(self):
        setup, cards = _p1_game(player1_hand=["Candy Golem"], player1_charge=5)
        actions = ActionValidator(setup.engine).get_valid_actions("player1")
        assert not any(a.card_id == cards["p1_hand_Candy Golem"].id for a in actions)

    def test_clone_copying_candy_golem_gains_nothing(self):
        """Ruling: the Clone card was played, not Candy Golem."""
        setup, cards = _p1_game(player1_hand=["Clone"], player1_in_play=["Candy Golem"], player1_charge=7)
        result = ActionExecutor(setup.engine).execute_play_card(
            "player1", cards["p1_hand_Clone"].id, target_card_id=cards["p1_inplay_Candy Golem"].id
        )
        assert result.success
        assert setup.player1.charge == 5  # 7 - 2, no +4


# ============================================================================
# Laundry Lad — "When played, your opponent loses all their Charge."
# ============================================================================

class TestLaundryLad:
    def test_opponent_loses_all_charge(self):
        setup, cards = _p1_game(player1_hand=["Laundry Lad"], player1_charge=4, player2_charge=5)
        result = _play(setup, setup.player1, cards["p1_hand_Laundry Lad"])
        assert result.success
        assert setup.player2.charge == 0
        assert setup.player1.charge == 2
        assert result.description == "Played Laundry Lad, Player 2 lost 5 Charge (2 Charge)"

    def test_opponent_with_no_charge(self):
        setup, cards = _p1_game(player1_hand=["Laundry Lad"], player2_charge=0)
        result = _play(setup, setup.player1, cards["p1_hand_Laundry Lad"])
        assert result.success
        assert setup.player2.charge == 0
        assert result.description == "Played Laundry Lad (2 Charge)"

    @pytest.mark.parametrize("protector", ["Beary", "Sock Sorcerer", "Bubble Blocker"])
    def test_immunity_does_not_protect_charge(self, protector):
        setup, cards = _p1_game(player1_hand=["Laundry Lad"], player2_in_play=[protector], player2_charge=5)
        _play(setup, setup.player1, cards["p1_hand_Laundry Lad"])
        assert setup.player2.charge == 0

    def test_works_on_player2_turn(self):
        setup, cards = create_game_with_cards(
            player2_hand=["Laundry Lad"], player1_charge=3, player2_charge=4,
            active_player="player2", turn_number=4,
        )
        assert _play(setup, setup.player2, cards["p2_hand_Laundry Lad"]).success
        assert setup.player1.charge == 0
        assert setup.player2.charge == 2

    def test_retriggers_when_replayed_after_toynado(self):
        setup, cards = _p1_game(
            player1_hand=["Laundry Lad", "Toynado"], player1_charge=7, player2_charge=5
        )
        lad = cards["p1_hand_Laundry Lad"]
        _play(setup, setup.player1, lad)
        assert setup.player2.charge == 0

        _play(setup, setup.player1, cards["p1_hand_Toynado"])
        assert lad in setup.player1.hand
        setup.player2.gain_charge(3)

        _play(setup, setup.player1, lad)
        assert setup.player2.charge == 0

    def test_twist_taking_laundry_lad_does_not_trigger(self):
        """Ruling: only playing the card from hand triggers it."""
        setup, cards = _p1_game(
            player1_hand=["Twist"], player2_in_play=["Laundry Lad"], player1_charge=7, player2_charge=3
        )
        _play(setup, setup.player1, cards["p1_hand_Twist"], [cards["p2_inplay_Laundry Lad"]])
        assert cards["p2_inplay_Laundry Lad"] in setup.player1.in_play
        assert setup.player2.charge == 3


# ============================================================================
# Copy / Clone ruling for targeted when-played Toys
# ============================================================================

class TestCopyDoesNotTrigger:
    def test_clone_copying_sock_serpent_breaks_nothing(self):
        setup, cards = _p1_game(
            player1_hand=["Clone"], player1_in_play=["Sock Serpent"],
            player2_in_play=["Knight"], player1_charge=7,
        )
        result = ActionExecutor(setup.engine).execute_play_card(
            "player1", cards["p1_hand_Clone"].id, target_card_id=cards["p1_inplay_Sock Serpent"].id
        )
        assert result.success
        assert cards["p2_inplay_Knight"].zone == Zone.IN_PLAY


# ============================================================================
# Resolution-time and HTTP-level coverage
# ============================================================================

class TestTargetChangesBeforeResolution:
    def test_empty_target_list_declines(self):
        setup, cards = _p1_game(player1_hand=["Sir Scares a lot"], player2_in_play=["Ka"])
        result = ActionExecutor(setup.engine).execute_play_card(
            "player1", cards["p1_hand_Sir Scares a lot"].id, target_card_ids=[]
        )
        assert result.success
        assert cards["p2_inplay_Ka"].zone == Zone.IN_PLAY

    def test_target_broken_after_enumeration_is_rejected(self):
        """A target that left play between valid-actions and play-card is refused, not re-broken."""
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player2_in_play=["Umbruh"], player2_charge=0)
        serpent, umbruh = cards["p1_hand_Sock Serpent"], cards["p2_inplay_Umbruh"]
        assert _play_action(setup, setup.player1, serpent).target_options == [umbruh.id]

        setup.engine._break_card(umbruh, setup.player2, was_in_play=True)  # Umbruh: +1 Charge
        assert setup.player2.charge == 1

        with pytest.raises(ValueError, match="Invalid target"):
            _play(setup, setup.player1, serpent, [umbruh])
        # Bypassing the executor: resolution re-checks validity, so no second break / trigger.
        assert setup.engine.play_card(setup.player1, serpent, target_ids=[umbruh.id])
        assert setup.player2.break_zone.count(umbruh) == 1
        assert setup.player2.charge == 1

    def test_scope_holds_when_player_kwarg_missing(self):
        """Resolution falls back to the source card's controller, never failing open."""
        setup, cards = _p1_game(player1_in_play=["Sock Serpent", "Ka"])
        serpent, ka = cards["p1_inplay_Sock Serpent"], cards["p1_inplay_Ka"]
        effect = next(e for e in EffectRegistry.get_effects(serpent) if isinstance(e, BreakTargetEffect))
        effect.apply(setup.game_state, targets=[ka], game_engine=setup.engine)  # no player=
        assert ka.zone == Zone.IN_PLAY


class TestRoutes:
    """Through the real FastAPI handlers (game-action routes otherwise lack HTTP coverage)."""

    @pytest.fixture
    def client_for(self):
        from fastapi.testclient import TestClient
        from api.app import app
        from api.game_service import get_game_service

        service = get_game_service()
        original_use_database = service.use_database
        service.use_database = False  # no tables in CI's in-memory SQLite
        injected = []

        def _inject(setup):
            service._cache[setup.game_state.game_id] = setup.engine
            injected.append(setup.game_state.game_id)
            return TestClient(app)

        yield _inject
        for game_id in injected:
            service._cache.pop(game_id, None)
        service.use_database = original_use_database

    def test_valid_actions_and_optional_play(self, client_for):
        setup, cards = _p1_game(player1_hand=["Sock Serpent"], player1_in_play=["Ka"], player2_in_play=["Knight"])
        client = client_for(setup)
        gid, serpent = setup.game_state.game_id, cards["p1_hand_Sock Serpent"]

        actions = client.get(f"/games/{gid}/valid-actions", params={"player_id": "player1"}).json()["valid_actions"]
        play = next(a for a in actions if a["action_type"] == "play_card" and a["card_id"] == serpent.id)
        assert play["min_targets"] == 0
        assert play["target_options"] == [cards["p2_inplay_Knight"].id]

        response = client.post(f"/games/{gid}/play-card", json={"player_id": "player1", "card_id": serpent.id})
        assert response.status_code == 200, response.text
        assert serpent.zone == Zone.IN_PLAY
        assert cards["p2_inplay_Knight"].zone == Zone.IN_PLAY

    def test_targeted_play_and_own_card_rejected(self, client_for):
        setup, cards = _p1_game(
            player1_hand=["Sir Scares a lot", "Sock Serpent"], player1_in_play=["Ka"], player2_in_play=["Knight"],
        )
        client = client_for(setup)
        gid = setup.game_state.game_id

        bad = client.post(f"/games/{gid}/play-card", json={
            "player_id": "player1", "card_id": cards["p1_hand_Sock Serpent"].id,
            "target_card_id": cards["p1_inplay_Ka"].id,
        })
        assert bad.status_code == 400
        assert cards["p1_inplay_Ka"].zone == Zone.IN_PLAY

        ok = client.post(f"/games/{gid}/play-card", json={
            "player_id": "player1", "card_id": cards["p1_hand_Sir Scares a lot"].id,
            "target_card_ids": [cards["p2_inplay_Knight"].id],
        })
        assert ok.status_code == 200, ok.text
        assert cards["p2_inplay_Knight"] in setup.player2.hand

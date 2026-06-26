"""
Board-state legend / short-label resolution (issue #338).

Pins three things:
1. build_card_labels/format_board_legend (card_loader.py) produce the
   expected Y1/O2-style label scheme over the AI's own hand+in_play and the
   opponent's in_play only.
2. The opponent's HAND is never labeled or shown - this game does not reveal
   hand contents to the opponent (see get_relevant_card_names, which scopes
   card_guidance lookups the same way), and a board legend must not leak it.
3. The enumerator's raw_string (which independently calls build_card_labels
   on the same root game_state) resolves tussle/ability targets to the exact
   same labels the legend would show for that card - the whole point of the
   change is that a label in a candidate sequence is resolvable via the
   legend in the same prompt.
"""

from conftest import create_game_with_cards
from game_engine.ai.enumerator import enumerate_sequences
from game_engine.ai.prompts.card_loader import build_card_labels, format_board_legend


def _scenario():
    """P1 Knight in play + CC; P2 has 2 hand cards and one in-play toy Knight can beat."""
    return create_game_with_cards(
        player1_hand=["Surge"],
        player1_in_play=["Knight"],
        player2_hand=["Ka", "Wizard"],
        player2_in_play=["Paper Plane"],
        player1_cc=5,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )


def test_build_card_labels_scheme():
    setup, _ = _scenario()
    gs = setup.game_state
    labels = build_card_labels(gs, "player1")

    p1 = gs.players["player1"]
    p2 = gs.players["player2"]

    surge = next(c for c in p1.hand if c.name == "Surge")
    knight = next(c for c in p1.in_play if c.name == "Knight")
    paper_plane = next(c for c in p2.in_play if c.name == "Paper Plane")

    # "Y" = the player passed as player_id, numbered hand-then-in_play.
    assert labels[surge.id] == "Y1"
    assert labels[knight.id] == "Y2"
    # "O" = the opponent, but only their in_play - their hand is hidden.
    assert labels[paper_plane.id] == "O1"

    # The opponent's hand cards get no label at all.
    ka = next(c for c in p2.hand if c.name == "Ka")
    wizard = next(c for c in p2.hand if c.name == "Wizard")
    assert ka.id not in labels
    assert wizard.id not in labels

    # Every labeled card got a unique label; nothing collides.
    assert len(set(labels.values())) == len(labels)


def test_build_card_labels_is_symmetric_per_perspective():
    """From player2's perspective, the prefixes swap (their own cards become Y)."""
    setup, _ = _scenario()
    gs = setup.game_state

    labels_p2 = build_card_labels(gs, "player2")
    paper_plane = next(c for c in gs.players["player2"].in_play if c.name == "Paper Plane")
    knight = next(c for c in gs.players["player1"].in_play if c.name == "Knight")

    assert labels_p2[paper_plane.id].startswith("Y")
    assert labels_p2[knight.id].startswith("O")


def test_format_board_legend_includes_every_hand_and_in_play_card():
    setup, _ = _scenario()
    gs = setup.game_state
    legend = format_board_legend(gs, "player1", setup.engine)

    for label in ("Y1", "Y2", "O1"):
        assert label in legend
    for name in ("Surge", "Knight", "Paper Plane"):
        assert name in legend

    # Toy stats are shown, Action cards don't get a bogus stat block.
    assert "STA]" in legend  # at least one Toy line has stats
    surge_line = next(line for line in legend.splitlines() if "Surge" in line)
    assert "STA" not in surge_line  # Surge is an Action card


def test_format_board_legend_excludes_opponent_hand():
    """The opponent's hand contents must never appear in the legend - this game
    does not reveal hand contents to the opponent, and a board legend showing
    the AI the opponent's exact hand would defeat that."""
    setup, _ = _scenario()
    legend = format_board_legend(setup.game_state, "player1", setup.engine)

    assert "OPP hand" not in legend
    assert "Ka" not in legend
    assert "Wizard" not in legend


def test_format_board_legend_in_play_stats_reflect_continuous_effects():
    """Ka's own-side +2 STR aura should show up in an ally's in_play STR via game_engine."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Ka", "Knight"],
        player2_hand=[],
        player2_in_play=[],
        player1_cc=5,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    legend_with_engine = format_board_legend(setup.game_state, "player1", setup.engine)
    knight_line = next(line for line in legend_with_engine.splitlines() if "Knight" in line)
    # Knight's base STR is 4; Ka's continuous +2 STR aura should push it to 6.
    assert "6 STR" in knight_line

    legend_without_engine = format_board_legend(setup.game_state, "player1", game_engine=None)
    knight_line_base = next(line for line in legend_without_engine.splitlines() if "Knight" in line)
    assert "4 STR" in knight_line_base


def test_enumerator_raw_string_uses_legend_labels_not_uuids():
    """tussle/activate target ids in raw_string must resolve via build_card_labels,
    matching exactly what format_board_legend would show for that same card."""
    setup, _ = _scenario()
    gs = setup.game_state
    sequences = enumerate_sequences(gs, "player1")

    labels = build_card_labels(gs, "player1")
    paper_plane = next(c for c in gs.players["player2"].in_play if c.name == "Paper Plane")
    expected_label = labels[paper_plane.id]
    assert expected_label == "O1"

    tussle_seqs = [s for s in sequences if "tussle Knight->" in s["raw_string"]]
    assert tussle_seqs, f"Expected at least one tussle sequence, got: {[s['raw_string'] for s in sequences]}"
    for seq in tussle_seqs:
        assert f"tussle Knight->{expected_label}" in seq["raw_string"]
        # No raw UUID (36-char, hyphenated) should leak into the display string.
        assert paper_plane.id not in seq["raw_string"]


def test_enumerator_play_card_target_uses_label():
    """play_card targets (e.g. Drop sleeping an in-play card) should also resolve
    to a short label, not a raw UUID - same fix as tussle/ability targets."""
    setup, _ = create_game_with_cards(
        player1_hand=["Drop"],
        player1_in_play=[],
        player2_hand=[],
        player2_in_play=["Knight"],
        player1_cc=3,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    gs = setup.game_state
    sequences = enumerate_sequences(gs, "player1")
    labels = build_card_labels(gs, "player1")
    knight = next(c for c in gs.players["player2"].in_play if c.name == "Knight")
    expected_label = labels[knight.id]
    assert expected_label == "O1"

    drop_seqs = [s for s in sequences if "play Drop->" in s["raw_string"]]
    assert drop_seqs, f"Expected a targeted Drop sequence, got: {[s['raw_string'] for s in sequences]}"
    for seq in drop_seqs:
        assert f"play Drop->{expected_label}" in seq["raw_string"]
        assert knight.id not in seq["raw_string"]


def test_enumerator_activate_ability_target_uses_label():
    """Archer's activate_ability target should also resolve to a short label, not a UUID."""
    setup, _ = create_game_with_cards(
        player1_hand=[],
        player1_in_play=["Archer"],
        player2_hand=[],
        player2_in_play=["Knight"],
        player1_cc=3,
        player2_cc=0,
        active_player="player1",
        turn_number=3,
    )
    gs = setup.game_state
    sequences = enumerate_sequences(gs, "player1")
    labels = build_card_labels(gs, "player1")
    knight = next(c for c in gs.players["player2"].in_play if c.name == "Knight")
    expected_label = labels[knight.id]
    assert expected_label == "O1"

    activate_seqs = [s for s in sequences if "activate Archer->" in s["raw_string"]]
    assert activate_seqs, f"Expected an Archer activation sequence, got: {[s['raw_string'] for s in sequences]}"
    for seq in activate_seqs:
        assert f"activate Archer->{expected_label}" in seq["raw_string"]
        assert knight.id not in seq["raw_string"]

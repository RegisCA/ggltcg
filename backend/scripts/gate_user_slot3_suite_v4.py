"""Non-mirror gate simulation for AI V4 using the User_Slot3 deck.

Runs a small suite (default 20 games): User_Slot3 vs 4 baseline decks
(5 games each) and prints high-signal metrics:
- Win/loss/draw + turn-limit hits
- Average turns per matchup
- Early-turn (T1/T2) unused CC distribution for Player 1 (User_Slot3)
- Counts of recurring warning/error "symptoms" observed in stdout/stderr

This is intended as a fast iteration aid to surface reproducible failure modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import io
import sys
from contextlib import redirect_stderr, redirect_stdout

# Add backend/src to path for imports (same pattern as simulation.cli)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulation.deck_loader import load_simulation_decks_dict
from simulation.runner import SimulationRunner


@dataclass(frozen=True)
class GateConfig:
    model: str = "gemini-2.5-flash-lite"
    ai_version: int = 4
    max_turns: int = 20
    games_per_opponent: int = 5
    opponents: tuple[str, ...] = (
        "Aggro_Rush",
        "Control_Ka",
        "Tempo_Charge",
        "Disruption",
    )


def _count_symptoms(text: str) -> dict[str, int]:
    # Keep these as simple substring counts for repeatability.
    patterns: dict[str, str] = {
        "json_parse_error": "JSON parse error",
        "invalid_sequence_index": "Invalid sequence index",
        "invalid_action_number": "Invalid action number",
        "didnt_specify_target": "AI didn't specify target",
        "ai_failed_to_select_action": "AI failed to select action",
        "plan_deviation": "Plan deviation",
        "cc_went_negative": "CC went negative",
        "sequence_rejected": "rejected:",
    }

    return {key: text.count(substr) for key, substr in patterns.items()}


def _merge_counts(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    merged = dict(a)
    for key, value in b.items():
        merged[key] = merged.get(key, 0) + value
    return merged


def _expected_active_player_id(turn: int) -> str:
    return "player1" if (turn % 2 == 1) else "player2"


def main() -> None:
    cfg = GateConfig()

    decks = load_simulation_decks_dict()
    user_deck = decks["User_Slot3"]

    runner = SimulationRunner(
        player1_model=cfg.model,
        player2_model=cfg.model,
        player1_ai_version=cfg.ai_version,
        player2_ai_version=cfg.ai_version,
        max_turns=cfg.max_turns,
        log_level="WARNING",
    )

    total_games = cfg.games_per_opponent * len(cfg.opponents)

    outcomes = {
        "player1_win": 0,
        "player2_win": 0,
        "draw": 0,
        "turn_limit_hits": 0,
        "errors": 0,
    }

    total_turns = 0

    # Early-turn unused CC (cc_end) for the ACTIVE player on turns 1 and 2
    early_unused_cc: list[int] = []

    symptom_counts: dict[str, int] = {}
    matchup_turns: dict[str, list[int]] = {}
    matchup_outcomes: dict[str, dict[str, int]] = {}

    game_number = 0

    for opp_name in cfg.opponents:
        opp_deck = decks[opp_name]
        matchup_key = f"User_Slot3 vs {opp_name}"
        matchup_turns[matchup_key] = []
        matchup_outcomes[matchup_key] = {"player1_win": 0, "player2_win": 0, "draw": 0, "turn_limit_hits": 0}

        for _ in range(cfg.games_per_opponent):
            game_number += 1

            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                result = runner.run_game(user_deck, opp_deck, game_number=game_number)

            captured = f"{buf_out.getvalue()}\n{buf_err.getvalue()}"
            symptom_counts = _merge_counts(symptom_counts, _count_symptoms(captured))

            if result.error_message:
                outcomes["errors"] += 1

            outcome_value = result.outcome.value
            outcomes[outcome_value] += 1
            matchup_outcomes[matchup_key][outcome_value] += 1

            if outcome_value == "draw" and result.turn_count == cfg.max_turns:
                outcomes["turn_limit_hits"] += 1
                matchup_outcomes[matchup_key]["turn_limit_hits"] += 1

            total_turns += result.turn_count
            matchup_turns[matchup_key].append(result.turn_count)

            # Early-turn unused CC for player1 on turns 1 and 2
            for turn in (1, 2):
                expected_player = _expected_active_player_id(turn)
                entry = next(
                    (
                        cc
                        for cc in result.cc_tracking
                        if cc.turn == turn and cc.player_id == expected_player
                    ),
                    None,
                )
                if entry is not None:
                    early_unused_cc.append(entry.cc_end)

    avg_turns = (total_turns / total_games) if total_games else 0.0

    print("=== User_Slot3 V4 Non-Mirror Gate (Suite) ===")
    print(f"Games: {total_games} ({cfg.games_per_opponent} each vs {', '.join(cfg.opponents)})")
    print(f"Model: {cfg.model} | AI v{cfg.ai_version} | Turn limit: {cfg.max_turns}")
    print()

    print("=== Outcomes (overall) ===")
    print(f"P1 wins: {outcomes['player1_win']}/{total_games}")
    print(f"P2 wins: {outcomes['player2_win']}/{total_games}")
    print(f"Draws: {outcomes['draw']}/{total_games}")
    print(f"Turn-limit hits: {outcomes['turn_limit_hits']}/{total_games}")
    print(f"Errors: {outcomes['errors']}/{total_games}")
    print(f"Avg turns: {avg_turns:.1f}")
    print()

    print("=== Outcomes (by matchup) ===")
    for matchup_key in cfg.opponents:
        key = f"User_Slot3 vs {matchup_key}"
        m = matchup_outcomes[key]
        turns = matchup_turns[key]
        m_avg_turns = (sum(turns) / len(turns)) if turns else 0.0
        print(f"{key}: P1 {m['player1_win']}/{cfg.games_per_opponent}, P2 {m['player2_win']}/{cfg.games_per_opponent}, Draw {m['draw']}/{cfg.games_per_opponent}, TL {m['turn_limit_hits']}/{cfg.games_per_opponent}, AvgTurns {m_avg_turns:.1f}")
    print()

    print("=== Early Turns (T1/T2) Unused CC (active player cc_end) ===")
    if early_unused_cc:
        samples = len(early_unused_cc)
        unused_ge_1 = sum(1 for x in early_unused_cc if x >= 1)
        unused_ge_2 = sum(1 for x in early_unused_cc if x >= 2)
        avg_unused = sum(early_unused_cc) / samples
        print(f"Samples: {samples}/{total_games * 2}")
        print(f"Avg unused CC: {avg_unused:.2f}")
        print(f"Unused CC >= 1: {unused_ge_1}/{samples}")
        print(f"Unused CC >= 2: {unused_ge_2}/{samples}")
    else:
        print("Samples: 0")
    print()

    print("=== Recurring Symptoms (counts in stdout/stderr) ===")
    for k in sorted(symptom_counts.keys()):
        print(f"{k}: {symptom_counts[k]}")


if __name__ == "__main__":
    main()

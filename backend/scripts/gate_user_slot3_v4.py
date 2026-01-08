"""Quick gate simulation for AI V4 using the User_Slot3 deck.

Runs a small number of mirror games (User_Slot3 vs User_Slot3) and prints
high-signal metrics for early iteration:
- Turn-limit hits (20 turns)
- Early-turn (T1/T2) unused CC distribution
- Errors / draws

This is intended as a fast "did we break planning?" check.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

# Add backend/src to path for imports (same pattern as simulation.cli)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulation.deck_loader import load_simulation_decks_dict
from simulation.runner import SimulationRunner


@dataclass(frozen=True)
class GateConfig:
    games: int = 20
    model: str = "gemini-2.5-flash-lite"
    ai_version: int = 4
    max_turns: int = 20


def _expected_active_player_id(turn: int) -> str:
    return "player1" if (turn % 2 == 1) else "player2"


def main() -> None:
    cfg = GateConfig()

    decks = load_simulation_decks_dict()
    deck = decks["User_Slot3"]

    runner = SimulationRunner(
        player1_model=cfg.model,
        player2_model=cfg.model,
        player1_ai_version=cfg.ai_version,
        player2_ai_version=cfg.ai_version,
        max_turns=cfg.max_turns,
    )

    turn_limit_hits = 0
    draws = 0
    errors = 0

    # Early-turn unused CC (cc_end) for active player on turns 1 and 2
    early_unused_cc: list[int] = []

    for game_number in range(1, cfg.games + 1):
        result = runner.run_game(deck, deck, game_number=game_number)

        if result.error_message:
            errors += 1

        if result.outcome.value == "draw":
            draws += 1
            if result.turn_count == cfg.max_turns:
                turn_limit_hits += 1

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

    total_games = cfg.games
    total_early_turns = total_games * 2

    early_missing = total_early_turns - len(early_unused_cc)

    unused_ge_2 = sum(1 for x in early_unused_cc if x >= 2)
    unused_ge_1 = sum(1 for x in early_unused_cc if x >= 1)

    avg_unused = (sum(early_unused_cc) / len(early_unused_cc)) if early_unused_cc else 0.0

    print("=== User_Slot3 V4 Gate ===")
    print(f"Games: {total_games}")
    print(f"Model: {cfg.model} | AI v{cfg.ai_version}")
    print(f"Turn limit: {cfg.max_turns}")
    print()

    print("=== Outcomes ===")
    print(f"Draws: {draws}/{total_games}")
    print(f"Turn-limit hits: {turn_limit_hits}/{total_games}")
    print(f"Errors: {errors}/{total_games}")
    print()

    print("=== Early Turns (T1/T2) Unused CC (active player cc_end) ===")
    print(f"Samples: {len(early_unused_cc)}/{total_early_turns} (missing={early_missing})")
    print(f"Avg unused CC: {avg_unused:.2f}")
    print(f"Unused CC >= 1: {unused_ge_1}/{len(early_unused_cc)}")
    print(f"Unused CC >= 2: {unused_ge_2}/{len(early_unused_cc)}")


if __name__ == "__main__":
    main()

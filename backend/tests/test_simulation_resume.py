"""
Tests for PR B3: resumable simulation runs with budget-exhaustion pause.

Covers:
- The skip-set bug fix: resume must skip exactly the persisted game_numbers
  even with gaps (e.g. games 1, 3, 7 persisted), not `game_number >
  completed_games` which breaks with out-of-order parallel completion.
- BudgetExhaustedError from a worker propagates into a clean "paused" state
  (status=budget_exhausted, no rows for unfinished games) and resume_simulation
  completes the rest.
- The regression guard: matchup_stats after a pause+resume must be identical
  to a single uninterrupted session over the same games -- this exercises
  _rehydrate_result_from_db, which rebuilds in-memory aggregates from
  persisted SimulationGameModel rows (needed because the in-memory
  SimulationResult only reflects games completed by the current process).
- pause_simulation() best-effort stop: queued (not-yet-started) games are
  skipped and the run ends up "paused".
- SimulationConfig round-trip: rpm/daily_request_budget persist in run.config
  and survive resume; old config JSON without the new keys still loads.

No real Gemini calls are made: SimulationRunner.run_game is monkeypatched.
Uses an in-memory SQLite DB (StaticPool) so all sessions in a test share the
same schema/data, mirroring the pattern in test_rate_limiter.py.
"""

import sys
import threading
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.db_models import Base, SimulationGameModel, SimulationRunModel  # noqa: E402
from game_engine.ai.rate_limiter import BudgetExhaustedError  # noqa: E402
from simulation import orchestrator as orchestrator_module  # noqa: E402
from simulation.config import DeckConfig, GameOutcome, GameResult, SimulationConfig  # noqa: E402
from simulation.orchestrator import SimulationOrchestrator  # noqa: E402


DECK_NAMES = ["DeckA", "DeckB"]


@pytest.fixture
def db_session_factory():
    """Fresh in-memory SQLite DB (shared across sessions via StaticPool)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _patch_deck_loading(monkeypatch):
    """Avoid touching real cards.csv / deck validation for these unit tests."""
    deck_dict = {
        name: DeckConfig(name=name, description="", cards=["Ka"] * 6)
        for name in DECK_NAMES
    }
    monkeypatch.setattr(
        orchestrator_module, "load_simulation_decks_dict", lambda: deck_dict
    )
    monkeypatch.setattr(orchestrator_module, "validate_deck_names", lambda *a, **k: [])
    monkeypatch.setattr(orchestrator_module, "validate_deck", lambda *a, **k: [])


@pytest.fixture(autouse=True)
def _patch_session_local(monkeypatch, db_session_factory):
    """Worker threads use the module-level SessionLocal directly (for thread
    safety); point it at the test DB instead of the real app database."""
    monkeypatch.setattr(orchestrator_module, "SessionLocal", db_session_factory)


def _make_orchestrator(session_factory) -> SimulationOrchestrator:
    """Build an orchestrator wired to the test DB (main session + worker threads)."""
    return SimulationOrchestrator(
        db=session_factory(),
        rate_limiter_session_factory=session_factory,
    )


def _fake_game_result(game_info: dict, outcome: GameOutcome = GameOutcome.PLAYER1_WIN) -> GameResult:
    winner_deck = game_info["deck1_name"] if outcome == GameOutcome.PLAYER1_WIN else None
    if outcome == GameOutcome.PLAYER2_WIN:
        winner_deck = game_info["deck2_name"]
    return GameResult(
        game_number=game_info["game_number"],
        deck1_name=game_info["deck1_name"],
        deck2_name=game_info["deck2_name"],
        player1_model="test-model",
        player2_model="test-model",
        outcome=outcome,
        winner_deck=winner_deck,
        turn_count=3,
        duration_ms=1,
        charge_tracking=[],
        action_log=[],
    )


def _deterministic_outcome(game_number: int) -> GameOutcome:
    """Deterministic (order-independent) outcome per game_number."""
    return [GameOutcome.PLAYER1_WIN, GameOutcome.PLAYER2_WIN, GameOutcome.DRAW][game_number % 3]


class TestResumeSkipsPersistedGamesWithGaps:
    def test_skips_exactly_the_persisted_game_numbers(self, monkeypatch, db_session_factory):
        session_factory, orch = db_session_factory, _make_orchestrator(db_session_factory)

        config = SimulationConfig(
            deck_names=DECK_NAMES, iterations_per_matchup=2, parallel_games=1, max_turns=5
        )
        run_id = orch.start_simulation(config)
        # total_games = 2x2 matchups * 2 iterations = 8

        # Pre-persist games 1, 3, 7 (gaps), leaving 2, 4, 5, 6, 8 to run.
        db = session_factory()
        for gn in (1, 3, 7):
            db.add(SimulationGameModel(
                run_id=run_id, game_number=gn, deck1_name="DeckA", deck2_name="DeckA",
                player1_model="m", player2_model="m", outcome="player1_win",
                winner_deck="DeckA", turn_count=1, duration_ms=1,
                charge_tracking=[], action_log=[],
            ))
        db.commit()
        db.close()

        seen_game_numbers = []

        def fake_run_game(self, deck1, deck2, game_number=1):
            seen_game_numbers.append(game_number)
            return _fake_game_result({
                "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
            })

        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game
        )

        orch.run_simulation(run_id)

        assert sorted(seen_game_numbers) == [2, 4, 5, 6, 8]

        db = session_factory()
        all_numbers = sorted(
            row[0] for row in db.query(SimulationGameModel.game_number)
            .filter(SimulationGameModel.run_id == run_id).all()
        )
        db.close()
        assert all_numbers == [1, 2, 3, 4, 5, 6, 7, 8]


class TestBudgetExhaustedPauseAndResume:
    def test_pauses_cleanly_and_resume_completes_the_rest(self, monkeypatch, db_session_factory):
        session_factory = db_session_factory
        orch = _make_orchestrator(session_factory)

        config = SimulationConfig(
            deck_names=DECK_NAMES, iterations_per_matchup=2, parallel_games=1, max_turns=5
        )
        run_id = orch.start_simulation(config)
        # total_games = 8

        exhaust_at = 4  # raise once we reach the 4th distinct game call

        call_count = {"n": 0}

        def fake_run_game(self, deck1, deck2, game_number=1):
            call_count["n"] += 1
            if call_count["n"] == exhaust_at:
                from datetime import datetime, timezone
                raise BudgetExhaustedError(resets_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
            return _fake_game_result({
                "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
            }, outcome=_deterministic_outcome(game_number))

        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game
        )

        result = orch.run_simulation(run_id)

        db = session_factory()
        run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
        assert run.status == "budget_exhausted"
        persisted_before_resume = run.completed_games
        # Fewer than total_games were persisted -- the exhausted/unfinished
        # games were not recorded.
        assert persisted_before_resume < 8
        db.close()

        assert result.resets_at is not None

        # Resume with a fresh orchestrator instance (as a real resume would be).
        orch2 = _make_orchestrator(session_factory)
        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game
        )
        final_result = orch2.resume_simulation(run_id)

        db = session_factory()
        run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
        assert run.status == "completed"
        assert run.completed_games == 8
        db.close()
        assert final_result.completed_games == 8


class TestMatchupStatsRegressionGuard:
    def test_pause_resume_matches_single_session_aggregates(self, monkeypatch, db_session_factory):
        """
        A run completed across a pause+resume must produce identical
        matchup_stats to a run completed in a single uninterrupted session
        over the same set of games. Outcomes are deterministic per
        game_number so both runs compute the same underlying games.
        """
        session_factory = db_session_factory

        config = SimulationConfig(
            deck_names=DECK_NAMES, iterations_per_matchup=2, parallel_games=1, max_turns=5
        )

        def fake_run_game_factory():
            def fake_run_game(self, deck1, deck2, game_number=1):
                return _fake_game_result({
                    "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
                }, outcome=_deterministic_outcome(game_number))
            return fake_run_game

        # --- Run A: single uninterrupted session ---
        orch_a = _make_orchestrator(session_factory)
        run_id_a = orch_a.start_simulation(config)
        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game_factory()
        )
        result_a = orch_a.run_simulation(run_id_a)

        # --- Run B: paused partway (via BudgetExhaustedError), then resumed ---
        orch_b = _make_orchestrator(session_factory)
        run_id_b = orch_b.start_simulation(config)

        call_count = {"n": 0}

        def fake_run_game_b(self, deck1, deck2, game_number=1):
            call_count["n"] += 1
            if call_count["n"] == 4:
                from datetime import datetime, timezone
                raise BudgetExhaustedError(resets_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
            return _fake_game_result({
                "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
            }, outcome=_deterministic_outcome(game_number))

        monkeypatch.setattr(orchestrator_module.SimulationRunner, "run_game", fake_run_game_b)
        orch_b.run_simulation(run_id_b)

        orch_b2 = _make_orchestrator(session_factory)
        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game_factory()
        )
        result_b = orch_b2.resume_simulation(run_id_b)

        stats_a = {k: v.to_dict() for k, v in result_a.matchup_stats.items()}
        stats_b = {k: v.to_dict() for k, v in result_b.matchup_stats.items()}
        assert stats_a == stats_b
        assert result_a.completed_games == result_b.completed_games == 8


class TestPauseSimulation:
    def test_pause_stops_queued_games_and_ends_paused(self, monkeypatch, db_session_factory):
        session_factory = db_session_factory
        orch = _make_orchestrator(session_factory)

        config = SimulationConfig(
            deck_names=DECK_NAMES, iterations_per_matchup=3, parallel_games=1, max_turns=5
        )
        run_id = orch.start_simulation(config)
        # total_games = 2x2 * 3 = 12

        first_game_started = threading.Event()
        may_pause = threading.Event()
        call_count = {"n": 0}

        def fake_run_game(self, deck1, deck2, game_number=1):
            call_count["n"] += 1
            if call_count["n"] == 1:
                first_game_started.set()
                # Give the pausing thread a chance to call pause_simulation
                # before this (already-running) game "finishes".
                may_pause.wait(timeout=5)
            return _fake_game_result({
                "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
            })

        monkeypatch.setattr(orchestrator_module.SimulationRunner, "run_game", fake_run_game)

        def pauser():
            first_game_started.wait(timeout=5)
            orch.pause_simulation(run_id)
            may_pause.set()

        pauser_thread = threading.Thread(target=pauser)
        pauser_thread.start()
        result = orch.run_simulation(run_id)
        pauser_thread.join(timeout=5)

        assert result.status.value == "paused"
        # Not all 12 games should have run (queued games were skipped).
        assert call_count["n"] < 12

        db = session_factory()
        run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
        assert run.status == "paused"
        db.close()


class TestConfigRoundTrip:
    def test_rpm_and_daily_budget_persist_and_survive_resume(self, monkeypatch, db_session_factory):
        session_factory = db_session_factory
        orch = _make_orchestrator(session_factory)

        config = SimulationConfig(
            deck_names=DECK_NAMES,
            iterations_per_matchup=1,
            parallel_games=1,
            max_turns=5,
            rpm=42,
            daily_request_budget=100,
        )
        run_id = orch.start_simulation(config)

        db = session_factory()
        run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
        assert run.config["rpm"] == 42
        assert run.config["daily_request_budget"] == 100
        db.close()

        def fake_run_game(self, deck1, deck2, game_number=1):
            return _fake_game_result({
                "game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name,
            })

        monkeypatch.setattr(orchestrator_module.SimulationRunner, "run_game", fake_run_game)
        orch.run_simulation(run_id)

        db = session_factory()
        run = db.query(SimulationRunModel).filter(SimulationRunModel.id == run_id).first()
        assert run.status == "completed"
        # Config survives a reload from the DB (as resume_simulation does).
        reloaded_config = SimulationConfig(**run.config)
        assert reloaded_config.rpm == 42
        assert reloaded_config.daily_request_budget == 100
        db.close()

    def test_old_config_json_without_new_keys_still_loads(self):
        """Old persisted run.config rows won't have rpm/daily_request_budget/
        parallel_games keys; SimulationConfig must still reconstruct via
        defaults."""
        old_config_json = {
            "deck_names": DECK_NAMES,
            "player1_model": "gemini-2.5-flash-lite",
            "player2_model": "gemini-2.5-flash-lite",
            "iterations_per_matchup": 10,
            "max_turns": 20,
        }
        config = SimulationConfig(**old_config_json)
        assert config.rpm is None
        assert config.daily_request_budget is None
        assert config.parallel_games == 10


class TestStatusPersistsWithoutInjectedSession:
    """Regression (found by the 2026-07-08 E2E run): the CLI constructs the
    orchestrator WITHOUT a db session, so _get_db() hands out a fresh session
    per call. run_simulation used the run object cached by start_simulation
    (bound to a different session) and committed the new session -- terminal
    statuses (completed/budget_exhausted) were never persisted; runs stayed
    "pending" in the DB forever."""

    def test_terminal_status_persists_via_fresh_sessions(
        self, monkeypatch, db_session_factory
    ):
        # Mimic the CLI: no injected session; every _get_db() call is fresh.
        monkeypatch.setattr(orchestrator_module, "get_db", lambda: iter([db_session_factory()]))

        def fake_run_game(self, deck1, deck2, game_number=1):
            return _fake_game_result(
                {"game_number": game_number, "deck1_name": deck1.name, "deck2_name": deck2.name},
                _deterministic_outcome(game_number),
            )

        monkeypatch.setattr(
            orchestrator_module.SimulationRunner, "run_game", fake_run_game
        )

        orch = SimulationOrchestrator(
            db=None, rate_limiter_session_factory=db_session_factory
        )
        config = SimulationConfig(
            deck_names=DECK_NAMES, iterations_per_matchup=1, player1_model="m", player2_model="m"
        )
        run_id = orch.start_simulation(config)
        orch.run_simulation(run_id, parallel_games=2)

        # Read back through a completely independent session.
        with db_session_factory() as verify:
            row = verify.query(SimulationRunModel).filter(
                SimulationRunModel.id == run_id
            ).one()
            assert row.status == "completed", (
                f"terminal status must be persisted (got '{row.status}'); "
                "run_simulation must mutate the run via its own session"
            )
            assert row.completed_games == row.total_games

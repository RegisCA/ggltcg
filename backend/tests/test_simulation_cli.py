"""
Tests for PR B4: CLI support for multi-day throttled batch runs.

Covers:
- --rpm / --daily-budget land in the SimulationConfig passed to the
  orchestrator.
- budget_exhausted + --wait: the CLI sleeps until resets_at (+ slack) and
  calls resume_simulation, looping until the run completes.
- budget_exhausted + --no-wait: prints the resume command and exits with
  EX_TEMPFAIL (75) instead of hanging or failing loudly.
- `resume` validates run status and delegates to orchestrator.resume_simulation.
- `status` prints progress + budget info.
- `list-runs` works (regression guard for the list_simulations -> list_runs
  bug fix).

The orchestrator and reporter are fully mocked -- no real DB, no real API
calls, no real sleeping (time.sleep is patched).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation import cli as cli_module  # noqa: E402
from simulation.config import SimulationStatus  # noqa: E402


def _make_result(status, run_id=1, total_games=4, completed_games=4, resets_at=None, error_message=None):
    result = MagicMock()
    result.status = status
    result.run_id = run_id
    result.total_games = total_games
    result.completed_games = completed_games
    result.resets_at = resets_at
    result.error_message = error_message
    return result


@pytest.fixture(autouse=True)
def _patch_deck_names(monkeypatch):
    """Avoid touching real cards.csv / simulation_decks.csv for these unit tests."""
    monkeypatch.setattr(cli_module, "_get_deck_names", lambda preset: ["DeckA", "DeckB"])


@pytest.fixture(autouse=True)
def _patch_reporter(monkeypatch):
    """No real report files written during tests."""
    fake_reporter = MagicMock()
    fake_reporter.save_report.return_value = "/tmp/fake_report.md"
    monkeypatch.setattr(cli_module, "SimulationReporter", lambda results: fake_reporter)


@pytest.fixture(autouse=True)
def _patch_sleep(monkeypatch):
    """Never actually sleep in tests."""
    monkeypatch.setattr(cli_module.time, "sleep", MagicMock())


@pytest.fixture
def runner():
    return CliRunner()


class TestThrottleFlagsPassedToConfig:
    def test_rpm_and_daily_budget_land_in_config(self, runner, monkeypatch):
        captured = {}

        mock_orch = MagicMock()
        mock_orch.start_simulation.side_effect = lambda config: captured.setdefault("config", config) or 1
        mock_orch.run_simulation.return_value = _make_result(SimulationStatus.COMPLETED)
        mock_orch.get_results.return_value = {
            "run_id": 1, "config": {}, "games": [],
        }
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(
            cli_module.cli,
            ["baseline", "--iterations", "2", "--rpm", "30", "--daily-budget", "500"],
        )

        assert result.exit_code == 0, result.output
        config = captured["config"]
        assert config.rpm == 30
        assert config.daily_request_budget == 500


class TestBudgetExhaustedWaitLoop:
    def test_wait_sleeps_until_reset_and_resumes_to_completion(self, runner, monkeypatch):
        resets_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        mock_orch = MagicMock()
        mock_orch.start_simulation.return_value = 7
        mock_orch.run_simulation.return_value = _make_result(
            SimulationStatus.BUDGET_EXHAUSTED, run_id=7, completed_games=2, total_games=4,
            resets_at=resets_at,
        )
        mock_orch.resume_simulation.return_value = _make_result(
            SimulationStatus.COMPLETED, run_id=7, completed_games=4, total_games=4,
        )
        mock_orch.get_status.return_value = {
            "budget": {"used_today": 500, "daily_budget": 500, "rpm": 30, "resets_at": resets_at.isoformat()}
        }
        mock_orch.get_results.return_value = {"run_id": 7, "config": {}, "games": []}
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(
            cli_module.cli,
            ["baseline", "--iterations", "2", "--rpm", "30", "--daily-budget", "500", "--wait"],
        )

        assert result.exit_code == 0, result.output
        cli_module.time.sleep.assert_called_once()
        # Slept at least the requested slack on top of a positive remaining wait.
        slept_seconds = cli_module.time.sleep.call_args[0][0]
        assert slept_seconds >= cli_module._RESET_SLACK_SECONDS
        mock_orch.resume_simulation.assert_called_once_with(7, parallel_games=10)
        assert "Simulation complete" in result.output

    def test_no_wait_prints_resume_command_and_exits_75(self, runner, monkeypatch):
        resets_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        mock_orch = MagicMock()
        mock_orch.start_simulation.return_value = 9
        mock_orch.run_simulation.return_value = _make_result(
            SimulationStatus.BUDGET_EXHAUSTED, run_id=9, completed_games=1, total_games=4,
            resets_at=resets_at,
        )
        mock_orch.get_status.return_value = {
            "budget": {"used_today": 500, "daily_budget": 500, "rpm": 30, "resets_at": resets_at.isoformat()}
        }
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(
            cli_module.cli,
            ["baseline", "--iterations", "2", "--rpm", "30", "--daily-budget", "500", "--no-wait"],
        )

        assert result.exit_code == cli_module.EX_TEMPFAIL
        assert "python -m simulation.cli resume 9" in result.output
        mock_orch.resume_simulation.assert_not_called()
        cli_module.time.sleep.assert_not_called()


class TestResumeCommand:
    def test_validates_and_delegates(self, runner, monkeypatch):
        mock_orch = MagicMock()
        mock_orch.get_status.return_value = {
            "status": "budget_exhausted", "completed_games": 3, "total_games": 4,
        }
        mock_orch.resume_simulation.return_value = _make_result(
            SimulationStatus.COMPLETED, run_id=42, completed_games=4, total_games=4,
        )
        mock_orch.get_results.return_value = {"run_id": 42, "config": {}, "games": []}
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["resume", "42"])

        assert result.exit_code == 0, result.output
        mock_orch.resume_simulation.assert_called_once_with(42, parallel_games=None)

    def test_rejects_non_resumable_status(self, runner, monkeypatch):
        mock_orch = MagicMock()
        mock_orch.get_status.return_value = {
            "status": "completed", "completed_games": 4, "total_games": 4,
        }
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["resume", "42"])

        assert result.exit_code != 0
        assert "Cannot resume" in result.output
        mock_orch.resume_simulation.assert_not_called()

    def test_unknown_run_id_errors(self, runner, monkeypatch):
        mock_orch = MagicMock()
        mock_orch.get_status.side_effect = ValueError("Simulation run 999 not found")
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["resume", "999"])

        assert result.exit_code != 0
        assert "not found" in result.output


class TestStatusCommand:
    def test_prints_progress_and_budget(self, runner, monkeypatch):
        mock_orch = MagicMock()
        mock_orch.get_status.return_value = {
            "run_id": 5,
            "status": "budget_exhausted",
            "total_games": 10,
            "completed_games": 4,
            "progress_pct": 40.0,
            "error_message": None,
            "budget": {
                "used_today": 500, "daily_budget": 500, "rpm": 30,
                "resets_at": "2026-07-09T00:00:00+00:00",
            },
        }
        mock_orch.get_results.return_value = {
            "matchup_stats": {
                "DeckA_vs_DeckB": {
                    "games_played": 4, "deck1_win_rate": 0.5, "deck2_win_rate": 0.5,
                }
            }
        }
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["status", "5"])

        assert result.exit_code == 0, result.output
        assert "budget_exhausted" in result.output
        assert "4/10" in result.output
        assert "500/500" in result.output
        assert "DeckA_vs_DeckB" in result.output

    def test_unknown_run_id_errors(self, runner, monkeypatch):
        mock_orch = MagicMock()
        mock_orch.get_status.side_effect = ValueError("Simulation run 999 not found")
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["status", "999"])

        assert result.exit_code != 0
        assert "not found" in result.output


class TestListRunsRegression:
    def test_list_runs_calls_list_runs_not_list_simulations(self, runner, monkeypatch):
        """Regression guard: cli.py previously called the nonexistent
        orchestrator.list_simulations(); the real method is list_runs()."""
        mock_orch = MagicMock()
        mock_orch.list_runs.return_value = [
            {
                "run_id": 1, "status": "completed", "total_games": 4, "completed_games": 4,
                "config": {"deck_names": ["DeckA", "DeckB"]},
                "created_at": "2026-07-01T00:00:00", "completed_at": "2026-07-01T00:05:00",
            }
        ]
        # Deliberately no list_simulations attribute configured beyond the
        # MagicMock auto-attr -- if cli.py called it we wouldn't catch that
        # via AttributeError since MagicMock auto-creates attrs, so assert
        # list_runs was in fact what got called.
        monkeypatch.setattr(cli_module, "SimulationOrchestrator", lambda: mock_orch)

        result = runner.invoke(cli_module.cli, ["list-runs", "--limit", "5"])

        assert result.exit_code == 0, result.output
        mock_orch.list_runs.assert_called_once_with(limit=5)
        assert "Run #1" in result.output
        assert "completed" in result.output

"""
Tests for PR B5: simulation API routes for batch runs.

Covers:
- StartSimulationRequest threading rpm/daily_request_budget/parallel_games
  into the SimulationConfig handed to the orchestrator, plus validation.
- POST /runs/{run_id}/resume: 404 unknown, 409 wrong status, 409 double
  resume (already in _active_simulations), 200 happy path spawns a
  background call.
- POST /runs/{run_id}/pause: happy path + error paths.
- GET /runs/{run_id} response includes the budget dict from get_status().

No real games, no Gemini calls, no real background work: the orchestrator
class is patched at the routes_simulation module level and background
threads (if any get spawned) call a monkeypatched no-op target.
"""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.app import app  # noqa: E402
from api import routes_simulation  # noqa: E402


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_active_simulations():
    """Ensure _active_simulations doesn't leak state between tests."""
    routes_simulation._active_simulations.clear()
    yield
    routes_simulation._active_simulations.clear()


@pytest.fixture(autouse=True)
def _override_get_db():
    """Avoid touching a real database: get_db just yields a MagicMock."""
    def _fake_get_db():
        yield MagicMock()

    app.dependency_overrides[routes_simulation.get_db] = _fake_get_db
    yield
    app.dependency_overrides.pop(routes_simulation.get_db, None)


def _budget_status(**overrides):
    base = {
        "used_today": 3,
        "daily_budget": 100,
        "rpm": 10,
        "resets_at": None,
    }
    base.update(overrides)
    return base


class TestStartSimulationConfigThreading:
    def test_rpm_daily_budget_and_parallel_games_round_trip(self):
        deck_names = ["DeckA"]
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch, \
                patch.object(routes_simulation, "is_valid_model_name", return_value=True), \
                patch("threading.Thread") as MockThread:
            instance = MockOrch.return_value
            instance.start_simulation.return_value = 42

            mock_thread = MagicMock()
            MockThread.return_value = mock_thread

            resp = client.post(
                "/admin/simulation/start",
                json={
                    "deck_names": deck_names,
                    "iterations_per_matchup": 1,
                    "rpm": 30,
                    "daily_request_budget": 500,
                    "parallel_games": 4,
                },
            )

            assert resp.status_code == 200, resp.text
            assert resp.json()["run_id"] == 42

            # Inspect the SimulationConfig object passed to start_simulation.
            called_config = instance.start_simulation.call_args[0][0]
            assert called_config.rpm == 30
            assert called_config.daily_request_budget == 500
            assert called_config.parallel_games == 4

    @pytest.mark.parametrize(
        "field,value",
        [
            ("rpm", 0),
            ("daily_request_budget", 0),
            ("parallel_games", 0),
            ("parallel_games", 21),
        ],
    )
    def test_out_of_range_values_are_rejected(self, field, value):
        payload = {
            "deck_names": ["DeckA"],
            "iterations_per_matchup": 1,
            field: value,
        }
        resp = client.post("/admin/simulation/start", json=payload)
        assert resp.status_code == 422


class TestResumeSimulationRoute:
    def test_resume_unknown_run_returns_404(self):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.side_effect = ValueError("Simulation run 999 not found")

            resp = client.post("/admin/simulation/runs/999/resume")

            assert resp.status_code == 404

    @pytest.mark.parametrize("status", ["running", "pending", "completed", "cancelled"])
    def test_resume_wrong_status_returns_409(self, status):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 1,
                "status": status,
                "budget": _budget_status(),
            }

            resp = client.post("/admin/simulation/runs/1/resume")

            assert resp.status_code == 409

    def test_resume_double_resume_returns_409(self):
        routes_simulation._active_simulations[1] = MagicMock()

        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 1,
                "status": "paused",
                "budget": _budget_status(),
            }

            resp = client.post("/admin/simulation/runs/1/resume")

            assert resp.status_code == 409

    @pytest.mark.parametrize("status", ["paused", "budget_exhausted", "failed"])
    def test_resume_happy_path_spawns_background_call(self, status):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch, \
                patch.object(routes_simulation, "_resume_simulation_background") as mock_bg:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 5,
                "status": status,
                "budget": _budget_status(),
            }

            resp = client.post("/admin/simulation/runs/5/resume")

            assert resp.status_code == 200, resp.text
            assert resp.json()["run_id"] == 5

            # Give the background thread a moment to invoke the (mocked) target.
            deadline = time.time() + 2
            while mock_bg.call_count == 0 and time.time() < deadline:
                time.sleep(0.01)

            mock_bg.assert_called_once_with(5)

            # Clean up the real thread spawned by the route.
            with routes_simulation._simulations_lock:
                thread = routes_simulation._active_simulations.pop(5, None)
            if thread is not None:
                thread.join(timeout=2)


class TestPauseSimulationRoute:
    def test_pause_unknown_run_returns_404(self):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.side_effect = ValueError("Simulation run 999 not found")

            resp = client.post("/admin/simulation/runs/999/pause")

            assert resp.status_code == 404

    def test_pause_not_running_returns_409(self):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 1,
                "status": "completed",
                "budget": _budget_status(),
            }

            resp = client.post("/admin/simulation/runs/1/pause")

            assert resp.status_code == 409

    def test_pause_orchestrator_declines_returns_409(self):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 1,
                "status": "running",
                "budget": _budget_status(),
            }
            instance.pause_simulation.return_value = False

            resp = client.post("/admin/simulation/runs/1/pause")

            assert resp.status_code == 409

    def test_pause_happy_path(self):
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 1,
                "status": "running",
                "budget": _budget_status(),
            }
            instance.pause_simulation.return_value = True

            resp = client.post("/admin/simulation/runs/1/pause")

            assert resp.status_code == 200
            assert resp.json() == {"status": "pause_requested", "run_id": 1}
            instance.pause_simulation.assert_called_once_with(1)


class TestRunStatusIncludesBudget:
    def test_get_run_status_includes_budget_dict(self):
        expected_budget = _budget_status(used_today=17, daily_budget=200, rpm=25)
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 7,
                "status": "running",
                "total_games": 10,
                "completed_games": 3,
                "budget": expected_budget,
            }

            resp = client.get("/admin/simulation/runs/7")

            assert resp.status_code == 200
            assert resp.json()["budget"] == expected_budget

    def test_get_run_status_budget_may_be_null_fields(self):
        """When no throttling is configured, budget fields are all null."""
        with patch.object(routes_simulation, "SimulationOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.get_status.return_value = {
                "run_id": 8,
                "status": "completed",
                "budget": {
                    "used_today": None,
                    "daily_budget": None,
                    "rpm": None,
                    "resets_at": None,
                },
            }

            resp = client.get("/admin/simulation/runs/8")

            assert resp.status_code == 200
            assert resp.json()["budget"] == {
                "used_today": None,
                "daily_budget": None,
                "rpm": None,
                "resets_at": None,
            }

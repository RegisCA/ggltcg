"""
Tests for PR A6: admin-access gating on /admin/* and /admin/simulation/*.

Covers:
- get_admin_emails() parsing of the ADMIN_EMAILS env var (comma-separated,
  case-insensitive, whitespace-tolerant, empty when unset).
- get_current_admin_user() dependency: missing/invalid token -> 401; unknown
  user -> 401; unconfigured allowlist -> 403 (fail closed, never open);
  authenticated-but-not-allowlisted -> 403; allowlisted -> passes through
  and returns the google_id.
- The email claim survives /auth/google (embedded at creation) and
  /auth/refresh (carried over from the old token), since admin gating reads
  it from the JWT rather than a DB column.

No real Google/Gemini calls; UserService.get_user_by_google_id is
monkeypatched so no real database is touched.
"""

import os
# MUST set JWT_SECRET_KEY before importing UserService (use CI value if set)
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_ci")

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import admin_auth as admin_auth_module  # noqa: E402
from api.admin_auth import get_admin_emails, get_current_admin_user  # noqa: E402
from api.database import get_db as real_get_db  # noqa: E402
from api.user_service import UserService  # noqa: E402


class TestGetAdminEmails:
    def test_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        assert get_admin_emails() == set()

    def test_empty_when_blank(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "   ")
        assert get_admin_emails() == set()

    def test_parses_comma_separated_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", " Alice@Example.com, bob@example.com ,,")
        assert get_admin_emails() == {"alice@example.com", "bob@example.com"}

    def test_reads_fresh_each_call(self, monkeypatch):
        """Not cached at import time -- a test (or a Render dashboard edit)
        changing the env var must take effect without a process restart."""
        monkeypatch.setenv("ADMIN_EMAILS", "a@example.com")
        assert get_admin_emails() == {"a@example.com"}
        monkeypatch.setenv("ADMIN_EMAILS", "b@example.com")
        assert get_admin_emails() == {"b@example.com"}


@pytest.fixture
def app_with_protected_route():
    app = FastAPI()

    @app.get("/protected")
    def protected(google_id: str = Depends(get_current_admin_user)):
        return {"google_id": google_id}

    def _fake_get_db():
        yield MagicMock()

    app.dependency_overrides[real_get_db] = _fake_get_db
    return app


@pytest.fixture
def client(app_with_protected_route):
    return TestClient(app_with_protected_route)


class TestGetCurrentAdminUser:
    def test_missing_authorization_header_is_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_malformed_header_is_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
        resp = client.get("/protected", headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    def test_invalid_token_is_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
        resp = client.get("/protected", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401

    def test_unknown_user_is_401(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
        monkeypatch.setattr(UserService, "get_user_by_google_id", lambda db, gid: None)
        token = UserService.create_jwt_token("some-google-id", email="admin@example.com")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_unconfigured_allowlist_is_403_even_for_a_real_user(self, client, monkeypatch):
        """Fail closed: an empty/unset ADMIN_EMAILS must never mean 'anyone
        with a valid session is admin'."""
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        monkeypatch.setattr(UserService, "get_user_by_google_id", lambda db, gid: MagicMock())
        token = UserService.create_jwt_token("some-google-id", email="admin@example.com")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_authenticated_but_not_allowlisted_is_403(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "someone-else@example.com")
        monkeypatch.setattr(UserService, "get_user_by_google_id", lambda db, gid: MagicMock())
        token = UserService.create_jwt_token("some-google-id", email="not-admin@example.com")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_token_without_email_claim_is_403(self, client, monkeypatch):
        """Tokens issued before this feature (no email claim) must not pass
        just because the allowlist happens to be configured."""
        monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
        monkeypatch.setattr(UserService, "get_user_by_google_id", lambda db, gid: MagicMock())
        token = UserService.create_jwt_token("some-google-id")  # no email=
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_allowlisted_email_passes_through(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", "Admin@Example.com")  # case mismatch on purpose
        monkeypatch.setattr(UserService, "get_user_by_google_id", lambda db, gid: MagicMock())
        token = UserService.create_jwt_token("the-google-id", email="admin@example.com")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == {"google_id": "the-google-id"}


class TestEmailClaimSurvivesTheAuthFlow:
    """The app persists no email column anywhere (see UserModel) -- admin
    gating depends entirely on the JWT's email claim surviving login and
    refresh. These pin that contract at the UserService level."""

    def test_create_jwt_token_embeds_email(self):
        token = UserService.create_jwt_token("gid", email="a@example.com")
        payload = UserService.decode_jwt_payload(token)
        assert payload["email"] == "a@example.com"
        assert payload["sub"] == "gid"

    def test_create_jwt_token_email_defaults_to_none(self):
        token = UserService.create_jwt_token("gid")
        payload = UserService.decode_jwt_payload(token)
        assert payload["email"] is None

    def test_verify_jwt_token_unchanged_return_contract(self):
        """verify_jwt_token must keep returning a bare google_id string --
        many existing routes depend on get_current_user's `str` contract."""
        token = UserService.create_jwt_token("gid", email="a@example.com")
        assert UserService.verify_jwt_token(token) == "gid"

"""
Admin-access gating for /admin/* and /admin/simulation/* routes.

Reuses the existing Google sign-in / JWT flow (see auth_routes.py) rather
than introducing a separate credential: any signed-in user gets a JWT, but
only a request whose token's "email" claim is in the ADMIN_EMAILS allowlist
may reach an admin route.

Fails closed: if ADMIN_EMAILS is unset or empty, every request is rejected
(403), including for an otherwise-valid, otherwise-legitimate user. An
unconfigured allowlist must never mean "everyone is admin".
"""

import os
import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .auth_routes import extract_bearer_token
from .database import get_db
from .user_service import UserService

logger = logging.getLogger(__name__)


def get_admin_emails() -> set[str]:
    """Read the ADMIN_EMAILS allowlist fresh from the environment.

    Comma-separated, case-insensitive. Read on every call (not cached at
    import time) so it can be changed without a process restart in tests,
    and so a missing/renamed env var doesn't silently freeze a stale value.
    """
    raw = os.getenv("ADMIN_EMAILS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


async def get_current_admin_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Session = Depends(get_db),
) -> str:
    """
    Dependency: require a valid JWT whose email claim is allowlisted.

    Returns:
        str: the authenticated user's Google ID

    Raises:
        HTTPException: 401 if the token is missing/invalid/for an unknown
            user; 403 if the user is authenticated but not allowlisted (or
            the allowlist is unconfigured).
    """
    token = extract_bearer_token(authorization)

    try:
        payload = UserService.decode_jwt_payload(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    google_id = payload["sub"]
    email = payload.get("email")

    user = UserService.get_user_by_google_id(db, google_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    admin_emails = get_admin_emails()
    if not admin_emails:
        logger.warning("Admin access denied: ADMIN_EMAILS is not configured")
        raise HTTPException(status_code=403, detail="Admin access is not configured")

    if not email or email.lower() not in admin_emails:
        raise HTTPException(status_code=403, detail="Not authorized for admin access")

    return google_id

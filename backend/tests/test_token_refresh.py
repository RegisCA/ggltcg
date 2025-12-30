"""
Test token refresh functionality.
"""

import os
# MUST set JWT_SECRET_KEY before importing UserService
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_tokens"

import pytest
from datetime import datetime, timedelta
import jwt
from api.user_service import UserService


def test_create_and_verify_new_token():
    """Test that we can create a new JWT token."""
    google_id = "test_user_12345"
    
    # Create first token
    token1 = UserService.create_jwt_token(google_id)
    
    # Verify it works
    verified_id = UserService.verify_jwt_token(token1)
    assert verified_id == google_id
    
    # Create second token (simulating refresh)
    token2 = UserService.create_jwt_token(google_id)
    
    # Both tokens should be valid for the same user
    verified_id2 = UserService.verify_jwt_token(token2)
    assert verified_id2 == google_id
    
    # Both tokens should work independently (refresh creates new valid token)
    assert verified_id == verified_id2


def test_expired_token_verification():
    """Test that expired tokens are rejected."""
    google_id = "test_user_expired"
    jwt_secret = os.getenv("JWT_SECRET_KEY", "test_secret_key_for_tokens")
    
    # Create an expired token (expired 1 hour ago)
    expiration = datetime.utcnow() - timedelta(hours=1)
    payload = {
        "sub": google_id,
        "exp": expiration,
        "iat": datetime.utcnow() - timedelta(hours=25)
    }
    expired_token = jwt.encode(
        payload,
        jwt_secret,
        algorithm="HS256"
    )
    
    # Verify that expired token is rejected
    with pytest.raises(ValueError, match="Token has expired"):
        UserService.verify_jwt_token(expired_token)


def test_token_has_24_hour_expiration():
    """Test that new tokens have 24-hour expiration."""
    google_id = "test_user_expiry"
    token = UserService.create_jwt_token(google_id)
    jwt_secret = os.getenv("JWT_SECRET_KEY", "test_secret_key_for_tokens")
    
    # Decode without verification to check expiration time
    decoded = jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"]
    )
    
    # Check that expiration is approximately 24 hours from now
    exp_time = datetime.utcfromtimestamp(decoded["exp"])
    now = datetime.utcnow()
    time_diff = (exp_time - now).total_seconds()
    
    # Should be approximately 24 hours (86400 seconds), allow 10 second tolerance
    assert abs(time_diff - 86400) < 10

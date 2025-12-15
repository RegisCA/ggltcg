"""
Authentication routes for Google OAuth 2.0.

Provides endpoints for user authentication, token verification, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Annotated, List
from datetime import datetime
import logging
import time
from collections import defaultdict

from .database import get_db
from .user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# Rate limiting
# Simple in-memory rate limiter (for production, use Redis or similar)
class RateLimiter:
    """Simple in-memory rate limiter for auth endpoints."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed based on rate limit."""
        now = time.time()
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[identifier].append(now)
        return True


# Rate limiter instances
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
profile_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


# Request/Response Models
class GoogleAuthRequest(BaseModel):
    """Request body for Google authentication."""
    token: str = Field(..., description="Google ID token from OAuth flow")


class AuthResponse(BaseModel):
    """Response for successful authentication."""
    jwt_token: str = Field(..., description="JWT token for API authentication")
    user: dict = Field(..., description="User profile information")


class UpdateProfileRequest(BaseModel):
    """Request body for profile updates."""
    display_name: Optional[str] = Field(None, description="Custom display name")


class UserProfileResponse(BaseModel):
    """User profile information."""
    google_id: str
    first_name: str
    display_name: str
    custom_display_name: Optional[str]
    created_at: str
    updated_at: str
    favorite_decks: Optional[List[List[str]]] = Field(None, description="Array of 3 favorite decks")


class UpdateFavoriteDeckRequest(BaseModel):
    """Request to update a favorite deck slot."""
    deck: List[str] = Field(..., min_length=6, max_length=6, description="Array of 6 card names")


class FavoriteDecksResponse(BaseModel):
    """Response with all favorite decks."""
    favorite_decks: List[List[str]] = Field(..., description="Array of 3 favorite decks")


# Dependency for JWT authentication
async def get_current_user(
    authorization: Annotated[str, Header()] = None,
    db: Session = Depends(get_db)
) -> str:
    """
    Dependency to extract and verify JWT token from Authorization header.
    
    Returns:
        str: User's Google ID
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = parts[1]
    
    try:
        google_id = UserService.verify_jwt_token(token)
        
        # Verify user exists in database
        user = UserService.get_user_by_google_id(db, google_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return google_id
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# Routes
@router.post("/google", response_model=AuthResponse)
async def authenticate_with_google(
    request: Request,
    auth_request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with Google OAuth token.
    
    Verifies the Google token, creates or retrieves user, and returns a JWT token.
    """
    # Rate limiting
    client_ip = request.client.host
    if not auth_rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    try:
        # Verify Google token
        google_info = UserService.verify_google_token(auth_request.token)
        
        # Extract user information
        google_id = google_info.get("sub")
        first_name = google_info.get("given_name", "User")
        
        if not google_id:
            raise HTTPException(status_code=400, detail="Invalid token: missing user ID")
        
        # Get or create user
        user = UserService.get_or_create_user(db, google_id, first_name)
        
        # Create JWT token for our API
        jwt_token = UserService.create_jwt_token(google_id)
        
        return AuthResponse(
            jwt_token=jwt_token,
            user={
                "google_id": user.google_id,
                "first_name": user.first_name,
                "display_name": user.display_name,
                "custom_display_name": user.custom_display_name
            }
        )
        
    except ValueError as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/verify")
async def verify_token(
    google_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify JWT token and return user status.
    
    Use this endpoint to check if a token is still valid.
    """
    user = UserService.get_user_by_google_id(db, google_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "valid": True,
        "google_id": user.google_id
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    google_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.
    """
    user = UserService.get_user_by_google_id(db, google_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfileResponse(
        google_id=user.google_id,
        first_name=user.first_name,
        display_name=user.display_name,
        custom_display_name=user.custom_display_name,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        favorite_decks=user.favorite_decks or []
    )


@router.put("/profile")
async def update_user_profile(
    request: Request,
    profile_update: UpdateProfileRequest,
    google_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's custom display name.
    
    Validates against profanity and length requirements.
    """
    # Rate limiting
    if not profile_rate_limiter.is_allowed(google_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    try:
        user, error = UserService.update_display_name(
            db,
            google_id,
            profile_update.display_name
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            "success": True,
            "user": {
                "google_id": user.google_id,
                "first_name": user.first_name,
                "display_name": user.display_name,
                "custom_display_name": user.custom_display_name
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Profile update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Profile update failed")


@router.get("/me/decks", response_model=FavoriteDecksResponse)
async def get_favorite_decks(
    google_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's favorite decks.
    """
    user = UserService.get_user_by_google_id(db, google_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Ensure we return 3 decks (fill with empty if needed)
    decks = user.favorite_decks or []
    while len(decks) < 3:
        decks.append([])
    
    return FavoriteDecksResponse(favorite_decks=decks[:3])


@router.put("/me/decks/{slot}")
async def update_favorite_deck(
    slot: int,
    deck_update: UpdateFavoriteDeckRequest,
    google_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a specific favorite deck slot (0, 1, or 2).
    
    Validates that:
    - Slot is 0, 1, or 2
    - Deck has exactly 6 cards
    - All cards exist in the game
    - Deck composition is valid
    """
    # Validate slot
    if slot not in [0, 1, 2]:
        raise HTTPException(status_code=400, detail="Slot must be 0, 1, or 2")
    
    user = UserService.get_user_by_google_id(db, google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate deck composition using game service logic
    from .game_service import GameService
    is_valid, error_msg = GameService.validate_deck(deck_update.deck)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Update the specific slot
    decks = user.favorite_decks or [[], [], []]
    while len(decks) < 3:
        decks.append([])
    
    decks[slot] = deck_update.deck
    user.favorite_decks = decks
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "slot": slot,
        "deck": deck_update.deck
    }

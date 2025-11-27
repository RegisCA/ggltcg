"""
User service for authentication and user management.

Handles user creation, retrieval, and profile updates with profanity filtering.
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests
from better_profanity import profanity
from sqlalchemy.orm import Session
import os
import logging

from .db_models import UserModel

logger = logging.getLogger(__name__)

# Load profanity filter
profanity.load_censor_words()

# Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class UserService:
    """Service for user authentication and management."""
    
    @staticmethod
    def verify_google_token(token: str) -> dict:
        """
        Verify Google OAuth token and extract user information.
        
        Args:
            token: Google ID token from OAuth flow
            
        Returns:
            dict: User information from Google (sub, given_name, email, etc.)
            
        Raises:
            ValueError: If token is invalid or verification fails
        """
        try:
            # Verify the token using Google's library
            # This validates signature, expiration, audience, and issuer
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                GOOGLE_CLIENT_ID
            )
            
            # Verify the token issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid token issuer')
            
            return idinfo
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise ValueError(f"Invalid token: {e}")
    
    @staticmethod
    def create_jwt_token(google_id: str) -> str:
        """
        Create JWT token for authenticated user sessions.
        
        Args:
            google_id: User's Google ID (subject identifier)
            
        Returns:
            str: JWT token string
        """
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            "sub": google_id,  # Subject - user's Google ID
            "exp": expiration,  # Expiration time
            "iat": datetime.utcnow()  # Issued at time
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def verify_jwt_token(token: str) -> str:
        """
        Verify JWT token and extract user's Google ID.
        
        Args:
            token: JWT token string
            
        Returns:
            str: User's Google ID
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            google_id = payload.get("sub")
            
            if not google_id:
                raise ValueError("Invalid token payload")
            
            return google_id
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
    
    @staticmethod
    def get_or_create_user(db: Session, google_id: str, first_name: str) -> UserModel:
        """
        Get existing user or create new user from Google OAuth data.
        
        Args:
            db: Database session
            google_id: User's Google ID (subject identifier)
            first_name: User's first name from Google profile
            
        Returns:
            UserModel: User database model
        """
        # Try to get existing user
        user = db.query(UserModel).filter(UserModel.google_id == google_id).first()
        
        if user:
            # Update last accessed time
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            return user
        
        # Create new user
        user = UserModel(
            google_id=google_id,
            first_name=first_name,
            custom_display_name=None
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user: {google_id}")
        return user
    
    @staticmethod
    def get_user_by_google_id(db: Session, google_id: str) -> Optional[UserModel]:
        """
        Get user by Google ID.
        
        Args:
            db: Database session
            google_id: User's Google ID
            
        Returns:
            Optional[UserModel]: User model or None if not found
        """
        return db.query(UserModel).filter(UserModel.google_id == google_id).first()
    
    @staticmethod
    def validate_display_name(display_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate custom display name for profanity and length.
        
        Args:
            display_name: Proposed display name
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check length
        if len(display_name) < 1:
            return False, "Display name cannot be empty"
        
        if len(display_name) > 50:
            return False, "Display name must be 50 characters or less"
        
        # Check for profanity
        if profanity.contains_profanity(display_name):
            return False, "Display name contains inappropriate language"
        
        return True, None
    
    @staticmethod
    def update_display_name(
        db: Session,
        google_id: str,
        display_name: Optional[str]
    ) -> tuple[UserModel, Optional[str]]:
        """
        Update user's custom display name.
        
        Args:
            db: Database session
            google_id: User's Google ID
            display_name: New display name (or None to clear)
            
        Returns:
            tuple: (updated_user, error_message)
            
        Raises:
            ValueError: If user not found
        """
        user = UserService.get_user_by_google_id(db, google_id)
        
        if not user:
            raise ValueError("User not found")
        
        # If setting a custom name, validate it
        if display_name:
            is_valid, error = UserService.validate_display_name(display_name)
            if not is_valid:
                return user, error
            
            user.custom_display_name = display_name
        else:
            # Clear custom name
            user.custom_display_name = None
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user, None

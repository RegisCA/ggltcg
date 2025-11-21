"""
Game code utilities for multiplayer lobby system.

Generates and validates 6-character game codes for easy sharing.
"""

import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from api.db_models import GameModel
import uuid


def generate_game_code() -> str:
    """
    Generate a random 6-character game code.
    
    Uses uppercase letters and digits, excluding ambiguous characters:
    - Excludes: 0, O, 1, I, L to avoid confusion
    - Length: 6 characters for ~2 billion combinations
    
    Returns:
        6-character game code (e.g., "ABC2D3")
    """
    # Character set without ambiguous chars
    chars = string.ascii_uppercase.replace('O', '').replace('I', '').replace('L', '')
    digits = string.digits.replace('0', '').replace('1', '')
    
    # Combine for good variety
    charset = chars + digits
    
    # Generate 6-character code
    code = ''.join(random.choices(charset, k=6))
    
    return code


def generate_unique_game_code(db: Session, max_attempts: int = 10) -> str:
    """
    Generate a unique game code that doesn't exist in the database.
    
    Args:
        db: Database session
        max_attempts: Maximum number of generation attempts
        
    Returns:
        Unique 6-character game code
        
    Raises:
        RuntimeError: If unable to generate unique code after max_attempts
    """
    for _ in range(max_attempts):
        code = generate_game_code()
        
        # Check if code already exists
        existing = db.query(GameModel).filter(GameModel.game_code == code).first()
        
        if not existing:
            return code
    
    raise RuntimeError(f"Failed to generate unique game code after {max_attempts} attempts")


def find_game_by_code(db: Session, game_code: str) -> Optional[GameModel]:
    """
    Find a game by its game code.
    
    Args:
        db: Database session
        game_code: 6-character game code
        
    Returns:
        GameModel if found, None otherwise
    """
    # Normalize to uppercase
    code = game_code.upper().strip()
    
    # Validate format
    if len(code) != 6 or not code.isalnum():
        return None
    
    return db.query(GameModel).filter(GameModel.game_code == code).first()


def is_game_code_valid(game_code: str) -> bool:
    """
    Validate game code format (without database check).
    
    Args:
        game_code: Code to validate
        
    Returns:
        True if format is valid
    """
    if not game_code:
        return False
    
    code = game_code.upper().strip()
    
    # Must be exactly 6 alphanumeric characters
    return len(code) == 6 and code.isalnum()

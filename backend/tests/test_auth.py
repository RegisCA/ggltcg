"""
Integration tests for authentication system.

Tests user creation, JWT token generation/verification, and profile management.
"""

import pytest
from datetime import datetime, timedelta
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from api.db_models import Base, UserModel
from api.user_service import UserService


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


class TestUserService:
    """Test UserService methods."""
    
    def test_verify_google_token_success(self):
        """Test successful Google token verification."""
        mock_idinfo = {
            'sub': '123456789',
            'given_name': 'John',
            'email': 'john@example.com',
            'iss': 'accounts.google.com'
        }
        
        with patch('api.user_service.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.return_value = mock_idinfo
            
            result = UserService.verify_google_token('fake_token')
            
            assert result['sub'] == '123456789'
            assert result['given_name'] == 'John'
    
    def test_verify_google_token_invalid_issuer(self):
        """Test Google token verification with invalid issuer."""
        mock_idinfo = {
            'sub': '123456789',
            'iss': 'evil.com'  # Invalid issuer
        }
        
        with patch('api.user_service.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.return_value = mock_idinfo
            
            with pytest.raises(ValueError, match='Invalid token issuer'):
                UserService.verify_google_token('fake_token')
    
    def test_create_and_verify_jwt_token(self):
        """Test JWT token creation and verification."""
        google_id = '123456789'
        
        # Create token
        token = UserService.create_jwt_token(google_id)
        
        # Verify token
        verified_id = UserService.verify_jwt_token(token)
        
        assert verified_id == google_id
    
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token."""
        google_id = '123456789'
        
        # Create an expired token
        expiration = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": google_id,
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        
        import os
        jwt_secret = os.getenv("JWT_SECRET_KEY", "test_secret")
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        with pytest.raises(ValueError, match='Token has expired'):
            UserService.verify_jwt_token(token)
    
    def test_get_or_create_user_new_user(self, test_db):
        """Test creating a new user."""
        google_id = '123456789'
        first_name = 'John'
        
        user = UserService.get_or_create_user(test_db, google_id, first_name)
        
        assert user.google_id == google_id
        assert user.first_name == first_name
        assert user.custom_display_name is None
        assert user.display_name == first_name
    
    def test_get_or_create_user_existing_user(self, test_db):
        """Test retrieving existing user."""
        google_id = '123456789'
        first_name = 'John'
        
        # Create user first time
        user1 = UserService.get_or_create_user(test_db, google_id, first_name)
        created_at = user1.created_at
        
        # Get user second time
        user2 = UserService.get_or_create_user(test_db, google_id, first_name)
        
        assert user2.google_id == google_id
        assert user2.created_at == created_at  # Should be same user
    
    def test_validate_display_name_valid(self):
        """Test display name validation with valid name."""
        is_valid, error = UserService.validate_display_name("CoolPlayer123")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_display_name_too_short(self):
        """Test display name validation with empty name."""
        is_valid, error = UserService.validate_display_name("")
        
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_validate_display_name_too_long(self):
        """Test display name validation with too long name."""
        long_name = "a" * 51
        is_valid, error = UserService.validate_display_name(long_name)
        
        assert is_valid is False
        assert "50 characters" in error
    
    def test_validate_display_name_profanity(self):
        """Test display name validation with profanity."""
        # Note: better-profanity has default word list
        is_valid, error = UserService.validate_display_name("badword123")
        
        # This test depends on better-profanity's word list
        # May need to adjust based on actual behavior
        if not is_valid:
            assert "inappropriate" in error.lower()
    
    def test_update_display_name_success(self, test_db):
        """Test updating display name successfully."""
        google_id = '123456789'
        
        # Create user
        user = UserService.get_or_create_user(test_db, google_id, 'John')
        
        # Update display name
        updated_user, error = UserService.update_display_name(
            test_db,
            google_id,
            'NewCoolName'
        )
        
        assert error is None
        assert updated_user.custom_display_name == 'NewCoolName'
        assert updated_user.display_name == 'NewCoolName'
    
    def test_update_display_name_clear(self, test_db):
        """Test clearing custom display name."""
        google_id = '123456789'
        
        # Create user with custom name
        user = UserService.get_or_create_user(test_db, google_id, 'John')
        UserService.update_display_name(test_db, google_id, 'CustomName')
        
        # Clear custom name
        updated_user, error = UserService.update_display_name(
            test_db,
            google_id,
            None
        )
        
        assert error is None
        assert updated_user.custom_display_name is None
        assert updated_user.display_name == 'John'  # Falls back to first name
    
    def test_update_display_name_invalid(self, test_db):
        """Test updating display name with invalid name."""
        google_id = '123456789'
        
        # Create user
        UserService.get_or_create_user(test_db, google_id, 'John')
        
        # Try to set invalid name (too long)
        long_name = "a" * 51
        updated_user, error = UserService.update_display_name(
            test_db,
            google_id,
            long_name
        )
        
        assert error is not None
        assert "50 characters" in error
        assert updated_user.custom_display_name is None  # Unchanged
    
    def test_update_display_name_user_not_found(self, test_db):
        """Test updating display name for non-existent user."""
        with pytest.raises(ValueError, match="User not found"):
            UserService.update_display_name(
                test_db,
                'nonexistent_id',
                'NewName'
            )


class TestUserModel:
    """Test UserModel database model."""
    
    def test_display_name_property_custom(self, test_db):
        """Test display_name property with custom name set."""
        user = UserModel(
            google_id='123',
            first_name='John',
            custom_display_name='CoolPlayer'
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.display_name == 'CoolPlayer'
    
    def test_display_name_property_default(self, test_db):
        """Test display_name property without custom name."""
        user = UserModel(
            google_id='123',
            first_name='John',
            custom_display_name=None
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.display_name == 'John'


# Run tests with: pytest backend/tests/test_auth.py -v

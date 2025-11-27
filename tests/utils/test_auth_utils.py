"""Tests for authentication utility functions"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_from_token,
    verify_token,
)
from tests.factories import UserFactory


class TestCreateAccessToken:
    """Tests for create_access_token function"""

    def test_create_access_token_with_valid_data(self):
        """Test creating access token with valid data"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token = create_access_token(token_data)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        # Token should have 3 parts separated by dots (JWT format)
        assert len(token.split(".")) == 3

    def test_access_token_contains_correct_claims(self):
        """Test that access token contains correct claims"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token = create_access_token(token_data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Assert
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_access_token_has_expiration(self):
        """Test that access token has expiration time"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token = create_access_token(token_data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Assert
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Expiration should be in the future
        assert exp_time > now
        # Expiration should be approximately ACCESS_TOKEN_EXPIRE_MINUTES from now
        expected_exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # Allow 5 second tolerance for test execution time
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    def test_access_token_with_custom_expiration(self):
        """Test creating access token with custom expiration"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        custom_expires = timedelta(minutes=30)

        # Act
        token = create_access_token(token_data, expires_delta=custom_expires)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Assert
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        expected_exp = now + custom_expires
        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    def test_access_token_is_unique(self):
        """Test that different tokens are generated for same data"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token1 = create_access_token(token_data)
        # Add delay to ensure different expiration times (exp is in seconds)
        import time

        time.sleep(1)
        token2 = create_access_token(token_data)

        # Assert - tokens should be different due to different exp times
        assert token1 != token2


class TestCreateRefreshToken:
    """Tests for create_refresh_token function"""

    def test_create_refresh_token_with_valid_data(self):
        """Test creating refresh token with valid data"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token = create_refresh_token(token_data)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_refresh_token_contains_correct_claims(self):
        """Test that refresh token contains correct claims"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        token = create_refresh_token(token_data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Assert
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_refresh_token_has_longer_expiration_than_access_token(self):
        """Test that refresh token expires later than access token"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}

        # Act
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])

        # Assert
        access_exp = access_payload["exp"]
        refresh_exp = refresh_payload["exp"]
        # Refresh token should expire later
        assert refresh_exp > access_exp


class TestVerifyToken:
    """Tests for verify_token function"""

    def test_verify_valid_token(self):
        """Test verifying a valid token"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        token = create_access_token(token_data)

        # Act
        payload = verify_token(token)

        # Assert
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_verify_invalid_token_returns_none(self):
        """Test that invalid token returns None"""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        payload = verify_token(invalid_token)

        # Assert
        assert payload is None

    def test_verify_expired_token_returns_none(self):
        """Test that expired token returns None"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        # Create token that expires immediately
        expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

        # Act
        payload = verify_token(expired_token)

        # Assert
        assert payload is None

    def test_verify_token_with_wrong_secret_returns_none(self):
        """Test that token signed with different secret returns None"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        token = create_access_token(token_data)

        # Manually decode with wrong secret to simulate tampering
        # We can't easily test this without modifying the token, so we test with malformed token
        malformed_token = token[:-5] + "xxxxx"  # Corrupt the signature

        # Act
        payload = verify_token(malformed_token)

        # Assert
        assert payload is None

    def test_verify_token_with_empty_string_returns_none(self):
        """Test that empty token returns None"""
        # Act
        payload = verify_token("")

        # Assert
        assert payload is None

    def test_verify_token_with_none_returns_none(self):
        """Test that None token returns None"""
        # Act
        payload = verify_token(None)

        # Assert
        assert payload is None


class TestGetCurrentUserFromToken:
    """Tests for get_current_user_from_token function"""

    def test_get_current_user_from_valid_access_token(self):
        """Test extracting user ID from valid access token"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        token = create_access_token(token_data)

        # Act
        extracted_user_id = get_current_user_from_token(token)

        # Assert
        assert extracted_user_id == user_id

    def test_get_current_user_from_refresh_token_returns_none(self):
        """Test that refresh token returns None (wrong token type)"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        refresh_token = create_refresh_token(token_data)

        # Act
        extracted_user_id = get_current_user_from_token(refresh_token)

        # Assert
        assert extracted_user_id is None

    def test_get_current_user_from_invalid_token_returns_none(self):
        """Test that invalid token returns None"""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        extracted_user_id = get_current_user_from_token(invalid_token)

        # Assert
        assert extracted_user_id is None

    def test_get_current_user_from_expired_token_returns_none(self):
        """Test that expired token returns None"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

        # Act
        extracted_user_id = get_current_user_from_token(expired_token)

        # Assert
        assert extracted_user_id is None


class TestGetCurrentUser:
    """Tests for get_current_user function"""

    def test_get_current_user_with_valid_token_and_existing_user(self, db_session: Session):
        """Test getting current user with valid token and existing user"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)

        # Act
        current_user = get_current_user(token, db_session)

        # Assert
        assert current_user is not None
        assert current_user.id == user.id
        assert current_user.email == user.email

    def test_get_current_user_with_bearer_prefix(self, db_session: Session):
        """Test that Bearer prefix is properly stripped"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)
        bearer_token = f"Bearer {token}"

        # Act
        current_user = get_current_user(bearer_token, db_session)

        # Assert
        assert current_user is not None
        assert current_user.id == user.id

    def test_get_current_user_with_bearer_prefix_case_insensitive(self, db_session: Session):
        """Test that Bearer prefix is case insensitive"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)
        bearer_token = f"bearer {token}"

        # Act
        current_user = get_current_user(bearer_token, db_session)

        # Assert
        assert current_user is not None
        assert current_user.id == user.id

    def test_get_current_user_with_invalid_token_raises_exception(self, db_session: Session):
        """Test that invalid token raises HTTPException"""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(invalid_token, db_session)

        assert exc_info.value.status_code == 401

    def test_get_current_user_with_expired_token_raises_exception(self, db_session: Session):
        """Test that expired token raises HTTPException"""
        # Arrange
        user_id = str(uuid4())
        token_data = {"sub": user_id}
        expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(expired_token, db_session)

        assert exc_info.value.status_code == 401

    def test_get_current_user_with_nonexistent_user_raises_exception(self, db_session: Session):
        """Test that token with nonexistent user raises HTTPException"""
        # Arrange
        nonexistent_user_id = str(uuid4())
        token_data = {"sub": nonexistent_user_id}
        token = create_access_token(token_data)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token, db_session)

        assert exc_info.value.status_code == 404

    def test_get_current_user_with_refresh_token_raises_exception(self, db_session: Session):
        """Test that refresh token raises HTTPException"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        refresh_token = create_refresh_token(token_data)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(refresh_token, db_session)

        assert exc_info.value.status_code == 401

    def test_get_current_user_preserves_user_data(self, db_session: Session):
        """Test that retrieved user has all original data"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)

        # Act
        current_user = get_current_user(token, db_session)

        # Assert
        assert current_user.email == user.email
        assert current_user.name == user.name
        assert current_user.avatar_url == user.avatar_url
        assert current_user.bio == user.bio
        assert current_user.position == user.position


class TestTokenRoundTrip:
    """Tests for token creation and verification round trip"""

    def test_token_round_trip_access_token(self):
        """Test creating and verifying access token round trip"""
        # Arrange
        user_id = str(uuid4())
        original_data = {"sub": user_id, "email": "test@example.com"}

        # Act
        token = create_access_token(original_data)
        verified_payload = verify_token(token)

        # Assert
        assert verified_payload is not None
        assert verified_payload["sub"] == original_data["sub"]
        assert verified_payload["email"] == original_data["email"]
        assert verified_payload["type"] == "access"

    def test_token_round_trip_refresh_token(self):
        """Test creating and verifying refresh token round trip"""
        # Arrange
        user_id = str(uuid4())
        original_data = {"sub": user_id}

        # Act
        token = create_refresh_token(original_data)
        verified_payload = verify_token(token)

        # Assert
        assert verified_payload is not None
        assert verified_payload["sub"] == original_data["sub"]
        assert verified_payload["type"] == "refresh"

    def test_token_round_trip_with_user_retrieval(self, db_session: Session):
        """Test complete round trip: create token, verify, extract user ID, retrieve user"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}

        # Act
        token = create_access_token(token_data)
        verified_payload = verify_token(token)
        extracted_user_id = get_current_user_from_token(token)
        retrieved_user = get_current_user(token, db_session)

        # Assert
        assert verified_payload is not None
        assert extracted_user_id == str(user.id)
        assert retrieved_user.id == user.id


class TestTokenEdgeCases:
    """Tests for edge cases in token handling"""

    def test_token_with_extra_whitespace(self, db_session: Session):
        """Test token with extra whitespace is handled"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)
        bearer_token = f"Bearer   {token}   "

        # Act
        current_user = get_current_user(bearer_token, db_session)

        # Assert
        assert current_user is not None
        assert current_user.id == user.id

    def test_token_with_multiple_bearer_prefixes(self, db_session: Session):
        """Test token with multiple Bearer prefixes raises 401"""
        # Arrange
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        token = create_access_token(token_data)
        # Multiple Bearer prefixes should be invalid
        malformed_token = f"Bearer Bearer {token}"

        # Act & Assert - should raise 401 because regex only removes one "Bearer" prefix
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(malformed_token, db_session)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_token_with_additional_claims(self):
        """Test token with additional claims is preserved"""
        # Arrange
        user_id = str(uuid4())
        token_data = {
            "sub": user_id,
            "email": "test@example.com",
            "role": "admin",
            "custom_claim": "custom_value",
        }

        # Act
        token = create_access_token(token_data)
        payload = verify_token(token)

        # Assert
        assert payload["sub"] == user_id
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["custom_claim"] == "custom_value"

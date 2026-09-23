"""
Authentication Service Module

This module provides comprehensive authentication functionality for the application.
It handles user authentication, token generation, and session management through
a well-structured service layer.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .database_connection_manager import DatabaseConnectionManager
from .exceptions import AuthenticationError, AuthorizationError
from .models import UserModel
from .token_generation_service import TokenGenerationService
from .user_repository import UserRepository


# Configure logging for the authentication module
logger = logging.getLogger(__name__)


@dataclass
class AuthenticationResult:
    """Represents the result of an authentication attempt.

    Attributes:
        is_authenticated: Whether the authentication was successful.
        user_identifier: The unique identifier of the authenticated user.
        access_token: The generated access token for the session.
        refresh_token: The generated refresh token for session renewal.
        token_expiration: The datetime when the access token expires.
        error_message: A descriptive error message if authentication failed.
    """
    is_authenticated: bool
    user_identifier: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiration: Optional[datetime] = None
    error_message: Optional[str] = None


class AuthenticationService:
    """Provides comprehensive authentication services for the application.

    This service handles user authentication, token management, and session
    lifecycle operations. It leverages the repository pattern for data access
    and implements industry-standard security practices for token generation.

    Attributes:
        user_repository: Repository for accessing user data.
        token_service: Service for generating and validating tokens.
        database_manager: Manager for database connections.
        max_login_attempts: Maximum number of allowed login attempts.
        token_expiration_minutes: Duration of token validity in minutes.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        token_generation_service: TokenGenerationService,
        database_connection_manager: DatabaseConnectionManager,
        max_login_attempts: int = 5,
        token_expiration_minutes: int = 30,
    ):
        """Initialize the AuthenticationService with required dependencies.

        Args:
            user_repository: Repository for accessing user data.
            token_generation_service: Service for generating security tokens.
            database_connection_manager: Manager for database connections.
            max_login_attempts: Maximum allowed login attempts before lockout.
            token_expiration_minutes: Token validity duration in minutes.
        """
        self.user_repository = user_repository
        self.token_generation_service = token_generation_service
        self.database_connection_manager = database_connection_manager
        self.max_login_attempts = max_login_attempts
        self.token_expiration_minutes = token_expiration_minutes

    def authenticate_user(
        self, username: str, password: str
    ) -> AuthenticationResult:
        """Authenticate a user with the provided credentials.

        This method performs the complete authentication flow, including
        credential validation, login attempt tracking, and token generation.

        Args:
            username: The username of the user attempting to authenticate.
            password: The password provided by the user.

        Returns:
            AuthenticationResult: The result of the authentication attempt,
                containing tokens if successful or an error message if failed.

        Raises:
            AuthenticationError: If the authentication process encounters
                an unexpected error.
        """
        try:
            # Retrieve the user from the repository
            user = self.user_repository.find_by_username(username)

            # Check if the user exists in the system
            if user is None:
                logger.warning(
                    f"Authentication attempt for non-existent user: {username}"
                )
                return AuthenticationResult(
                    is_authenticated=False,
                    error_message="Authentication failed. Please check your credentials and try again.",
                )

            # Check if the account is locked due to excessive login attempts
            if user.failed_login_attempts >= self.max_login_attempts:
                logger.warning(
                    f"Authentication attempt for locked account: {username}"
                )
                return AuthenticationResult(
                    is_authenticated=False,
                    error_message="Your account has been locked due to too many failed login attempts. "
                    "Please contact the system administrator to unlock your account.",
                )

            # Verify the provided password against the stored hash
            if not self._verify_password(password, user.password_hash, user.salt):
                # Increment the failed login attempts counter
                self.user_repository.increment_failed_attempts(user.user_identifier)
                logger.info(
                    f"Failed authentication attempt for user: {username}"
                )
                return AuthenticationResult(
                    is_authenticated=False,
                    error_message="Authentication failed. Please check your credentials and try again.",
                )

            # Reset failed login attempts on successful authentication
            self.user_repository.reset_failed_attempts(user.user_identifier)

            # Generate access and refresh tokens
            access_token = self.token_generation_service.generate_access_token(
                user.user_identifier
            )
            refresh_token = self.token_generation_service.generate_refresh_token(
                user.user_identifier
            )

            # Calculate token expiration time
            token_expiration = datetime.utcnow() + timedelta(
                minutes=self.token_expiration_minutes
            )

            # Log successful authentication
            logger.info(f"User successfully authenticated: {username}")

            # Return successful authentication result
            return AuthenticationResult(
                is_authenticated=True,
                user_identifier=user.user_identifier,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiration=token_expiration,
            )

        except Exception as exception:
            logger.error(
                f"An unexpected error occurred during authentication: {exception}"
            )
            raise AuthenticationError(
                f"An unexpected error occurred during the authentication process. "
                f"Please try again later or contact support. Error details: {exception}"
            )

    def _verify_password(
        self, password: str, stored_hash: str, salt: str
    ) -> bool:
        """Verify a password against a stored hash.

        This method uses HMAC-based comparison to prevent timing attacks.

        Args:
            password: The plaintext password to verify.
            stored_hash: The stored password hash to compare against.
            salt: The salt used in the original hashing process.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        # Hash the provided password with the stored salt
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(
            computed_hash.hex(), stored_hash
        )

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .db import DBManager
from .exceptions import AuthenticationError
from .models import UserModel
from .tokens import TokenService
from .users import UserRepo

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    authenticated: bool
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class AuthService:

    def __init__(
        self,
        users: UserRepo,
        tokens: TokenService,
        db: DBManager,
        max_attempts: int = 5,
        token_ttl_min: int = 30,
    ):
        self.users = users
        self.tokens = tokens
        self.db = db
        self.max_attempts = max_attempts
        self.token_ttl_min = token_ttl_min

    def authenticate(self, username: str, password: str) -> AuthResult:
        try:
            user = self.users.find_by_username(username)

            if user is None:
                logger.warning("auth attempt for unknown user: %s", username)
                return AuthResult(authenticated=False, error="bad credentials")

            if user.failed_login_attempts >= self.max_attempts:
                logger.warning("auth attempt on locked account: %s", username)
                return AuthResult(authenticated=False, error="account locked")

            if not self._check_password(password, user.password_hash, user.salt):
                self.users.increment_failed_attempts(user.id)
                logger.info("failed auth for user: %s", username)
                return AuthResult(authenticated=False, error="bad credentials")

            self.users.reset_failed_attempts(user.id)

            access = self.tokens.create_access(user.id)
            refresh = self.tokens.create_refresh(user.id)
            expires = datetime.utcnow() + timedelta(minutes=self.token_ttl_min)

            logger.info("authenticated: %s", username)

            return AuthResult(
                authenticated=True,
                user_id=user.id,
                access_token=access,
                refresh_token=refresh,
                expires_at=expires,
            )
        except Exception as exc:
            logger.error("auth error: %s", exc)
            raise AuthenticationError(f"auth failed: {exc}") from exc

    def _check_password(self, password: str, stored_hash: str, salt: str) -> bool:
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100_000
        )
        return hmac.compare_digest(computed.hex(), stored_hash)

"""
Auth Service (Skeleton).

Quản lý xác thực và phân quyền:
- JWT Token management
- 2FA (TOTP)
- Session management
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from loguru import logger

from configs.settings import get_settings


@dataclass
class AuthToken:
    """JWT-like auth token."""

    user_id: str
    token: str
    expires_at: float
    is_2fa_verified: bool = False


class AuthService:
    """
    Authentication service skeleton.

    Handles:
    - User registration / login
    - JWT token generation / validation
    - 2FA TOTP verification
    """

    def __init__(self):
        self.settings = get_settings()
        self._tokens: dict[str, AuthToken] = {}

    def generate_token(self, user_id: str, ttl: int = 3600) -> AuthToken:
        """Tạo auth token cho user."""
        token_str = secrets.token_urlsafe(32)
        token = AuthToken(
            user_id=user_id,
            token=token_str,
            expires_at=time.time() + ttl,
        )
        self._tokens[token_str] = token
        logger.info(f"Token generated for user: {user_id}")
        return token

    def validate_token(self, token: str) -> AuthToken | None:
        """Validate token, trả về None nếu không hợp lệ."""
        auth = self._tokens.get(token)
        if auth is None:
            return None
        if time.time() > auth.expires_at:
            del self._tokens[token]
            return None
        return auth

    def hash_password(self, password: str) -> str:
        """Hash password sử dụng HMAC-SHA256."""
        return hmac.new(
            self.settings.hmac_secret_key.encode(),
            password.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Xác minh password."""
        return hmac.compare_digest(self.hash_password(password), hashed)

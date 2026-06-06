import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import jwt
from fastapi import Request
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.errors import AppError


class RateLimiter(Protocol):
    """Provider-neutral contract for a future real rate-limit implementation."""

    async def check(self, request: Request, scope: str) -> None:
        """Raise an application error when the request exceeds its configured limit."""


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


class TokenManager:
    def __init__(self, settings: Settings) -> None:
        if settings.jwt_secret is None:
            raise AppError(
                code="configuration_error",
                message="JWT authentication is not configured",
                status_code=503,
            )
        self.settings = settings
        self.secret = settings.jwt_secret.get_secret_value()

    def create_access_token(self, user_id: UUID, role: str) -> str:
        return self._encode(
            subject=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self.settings.access_token_expire_minutes),
            extra={"role": role},
        )

    def create_refresh_token(self, user_id: UUID, token_id: UUID) -> str:
        return self._encode(
            subject=user_id,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self.settings.refresh_token_expire_days),
            token_id=token_id,
        )

    def decode(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.settings.jwt_algorithm],
                options={"require": ["exp", "iat", "jti", "sub", "type"]},
            )
        except InvalidTokenError as exc:
            raise authentication_error("Invalid or expired token") from exc
        if payload.get("type") != expected_type:
            raise authentication_error("Invalid token type")
        return payload

    def _encode(
        self,
        *,
        subject: UUID,
        token_type: str,
        expires_delta: timedelta,
        token_id: UUID | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(subject),
            "type": token_type,
            "jti": str(token_id or uuid4()),
            "iat": now,
            "exp": now + expires_delta,
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, self.secret, algorithm=self.settings.jwt_algorithm)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authentication_error(message: str = "Authentication required") -> AppError:
    return AppError(code="authentication_required", message=message, status_code=401)


def authorization_error(message: str = "Insufficient permissions") -> AppError:
    return AppError(code="forbidden", message=message, status_code=403)

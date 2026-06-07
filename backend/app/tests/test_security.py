from uuid import uuid4

import pytest

from app.core.config import Environment, Settings
from app.core.errors import AppError
from app.core.security import RateLimiter, TokenManager, TokenType


def test_rate_limiter_contract_requires_check_hook() -> None:
    assert RateLimiter.check.__name__ == "check"


def test_token_expiration_uses_configuration() -> None:
    manager = TokenManager(
        Settings(
            app_env=Environment.TEST,
            jwt_secret="test-secret-that-is-long-enough-for-token-tests",
            access_token_expire_minutes=7,
        )
    )

    payload = manager.decode(
        manager.create_access_token(uuid4(), "PATIENT"),
        TokenType.ACCESS,
    )

    assert payload["exp"] - payload["iat"] == 7 * 60


def test_missing_jwt_configuration_fails_clearly() -> None:
    with pytest.raises(AppError, match="JWT authentication is not configured"):
        TokenManager(Settings(app_env=Environment.TEST, jwt_secret=""))

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Environment, Settings
from app.core.rate_limit import RateLimitMiddleware


def test_login_account_budget_and_body_limit(client: TestClient) -> None:
    for _ in range(20):
        response = client.post(
            "/api/v1/auth/login", json={"email": "limited@example.com", "password": "invalid"}
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "limited@example.com", "password": "invalid"}
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            content=b"x" * 8193,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


async def test_production_storage_failure_denies_requests() -> None:
    settings = Settings(app_env=Environment.TEST)
    settings.app_env = Environment.PRODUCTION
    middleware = RateLimitMiddleware(lambda: None, settings)

    class OfflineRedis:
        async def eval(self, *args: Any) -> int:
            raise ConnectionError("offline")

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "path": "/api/v1/users/me",
            "headers": [],
            "client": ("127.0.0.1", 1),
            "app": SimpleNamespace(state=SimpleNamespace(redis=OfflineRedis())),
        }
    )

    async def never_called(request: Request) -> Any:
        raise AssertionError("Rate-store failure must not invoke the application")

    response = await middleware.dispatch(request, never_called)
    assert response.status_code == 503


def test_api_body_limit_also_bounds_streams_without_content_length(client: TestClient) -> None:
    response = client.post(
        "/api/v1/medications",
        content=iter([b"x" * 32768, b"y" * 32769]),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413

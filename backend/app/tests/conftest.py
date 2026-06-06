import asyncio
import socket
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Environment, Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def is_loopback(address: object) -> bool:
        if not isinstance(address, tuple) or not address:
            return True
        host = address[0]
        return isinstance(host, str) and (host in {"localhost", "::1"} or host.startswith("127."))

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if not is_loopback(address):
            raise AssertionError(f"External network calls are not allowed during tests: {address}")
        original_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if not is_loopback(address):
            raise AssertionError(f"External network calls are not allowed during tests: {address}")
        return original_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env=Environment.TEST,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        api_cors_origins=["https://mobile.test"],
        jwt_secret="test-secret-that-is-long-enough-for-auth-tests",
        caregiver_invite_token_return_enabled=True,
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(test_settings)) as test_client:
        app = test_client.app
        assert isinstance(app, FastAPI)
        engine: AsyncEngine = app.state.engine
        asyncio.run(_create_tables(engine))
        yield test_client
        asyncio.run(_drop_tables(engine))


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _drop_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture
def strong_password() -> str:
    return "StrongPassword1!"


def register_user(
    client: TestClient,
    *,
    email: str = "patient@example.com",
    password: str = "StrongPassword1!",
    role: str = "PATIENT",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "role": role,
            "timezone": "America/Chicago",
            "accessibility_preferences": {"large_text": True},
        },
    )
    assert response.status_code == 201
    payload: dict[str, Any] = response.json()
    return payload

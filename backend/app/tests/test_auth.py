import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.tests.conftest import register_user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_registration_hashes_password_and_normalizes_email(
    client: TestClient, strong_password: str
) -> None:
    tokens = register_user(client, email="  Patient@Example.COM ", password=strong_password)

    response = client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["email"] == "patient@example.com"
    assert "password_hash" not in response.json()

    async def read_user() -> User:
        app = client.app
        assert isinstance(app, FastAPI)
        factory: async_sessionmaker[AsyncSession] = app.state.session_factory
        async with factory() as session:
            user = await session.scalar(select(User))
            assert user is not None
            return user

    stored_user = asyncio.run(read_user())
    assert stored_user.password_hash != strong_password
    assert stored_user.password_hash.startswith("$argon2")


def test_registration_rejects_weak_password_and_public_admin(client: TestClient) -> None:
    weak_response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "weak", "full_name": "Weak User"},
    )
    admin_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "StrongPassword1!",
            "full_name": "Admin User",
            "role": "ADMIN",
        },
    )

    assert weak_response.status_code == 422
    assert "weak" not in weak_response.text
    assert admin_response.status_code == 422


def test_registration_rejects_duplicate_email(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "PATIENT@example.com",
            "password": "StrongPassword1!",
            "full_name": "Duplicate User",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_conflict"


def test_login_success_and_failure(client: TestClient, strong_password: str) -> None:
    register_user(client, password=strong_password)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "PATIENT@example.com", "password": strong_password},
    )
    failure = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@example.com", "password": "WrongPassword1!"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert failure.status_code == 401
    assert failure.json()["error"]["code"] == "authentication_required"


def test_protected_endpoint_rejects_unauthenticated_request(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_refresh_rotates_token_and_logout_revokes_it(client: TestClient) -> None:
    tokens = register_user(client)

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    reused_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    refreshed = refresh_response.json()
    logout_response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": refreshed["refresh_token"]}
    )
    after_logout = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refreshed["refresh_token"]}
    )

    assert refresh_response.status_code == 200
    assert refreshed["refresh_token"] != tokens["refresh_token"]
    assert reused_response.status_code == 401
    assert logout_response.status_code == 204
    assert after_logout.status_code == 401


def test_soft_delete_revokes_access_and_refresh_tokens(client: TestClient) -> None:
    tokens = register_user(client)

    delete_response = client.delete("/api/v1/users/me", headers=bearer(tokens["access_token"]))
    me_response = client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@example.com", "password": "StrongPassword1!"},
    )

    assert delete_response.status_code == 204
    assert me_response.status_code == 401
    assert refresh_response.status_code == 401
    assert login_response.status_code == 401


def test_update_current_user(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.patch(
        "/api/v1/users/me",
        headers=bearer(tokens["access_token"]),
        json={
            "full_name": "Updated User",
            "timezone": "UTC",
            "accessibility_preferences": {"reduce_motion": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated User"
    assert response.json()["accessibility_preferences"] == {"reduce_motion": True}


def test_update_current_user_rejects_unknown_timezone(client: TestClient) -> None:
    tokens = register_user(client)

    response = client.patch(
        "/api/v1/users/me",
        headers=bearer(tokens["access_token"]),
        json={"timezone": "Mars/Olympus_Mons"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_role_dependency_rejects_insufficient_permissions(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    @app.get("/test-admin")
    async def admin_only(
        user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    ) -> dict[str, str]:
        return {"role": user.role.value}

    tokens = register_user(client)
    response = client.get("/test-admin", headers=bearer(tokens["access_token"]))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"

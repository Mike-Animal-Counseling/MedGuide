from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import get_database_health_checker, get_redis_health_checker


class AvailableChecker:
    async def check(self) -> None:
        return None


class UnavailableChecker:
    async def check(self) -> None:
        raise ConnectionError("test-only unavailable service")


def test_health_endpoint_returns_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "medguide-api"}
    assert str(UUID(response.headers["X-Request-ID"])) == response.headers["X-Request-ID"]


def test_ready_checks_database_and_redis(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_database_health_checker] = AvailableChecker
    app.dependency_overrides[get_redis_health_checker] = AvailableChecker

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "services": {"database": "available", "redis": "available"},
    }


def test_ready_returns_consistent_error_when_dependency_is_unavailable(
    client: TestClient,
) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_database_health_checker] = UnavailableChecker
    app.dependency_overrides[get_redis_health_checker] = AvailableChecker

    response = client.get(
        "/ready",
        headers={"X-Request-ID": "c170e1f1-1723-4bb4-9f42-b3863583e0f1"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "Required services are unavailable",
            "request_id": "c170e1f1-1723-4bb4-9f42-b3863583e0f1",
            "details": {
                "services": {"database": "unavailable", "redis": "available"},
            },
        }
    }

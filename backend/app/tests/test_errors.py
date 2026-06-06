from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app


def test_application_error_uses_consistent_response(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    @app.get("/test-error")
    async def test_error() -> None:
        raise AppError(code="test_error", message="Test error", status_code=409)

    response = client.get("/test-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "test_error"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_http_error_uses_consistent_response(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    @app.get("/test-http-error")
    async def test_http_error() -> None:
        raise HTTPException(status_code=404, detail="Resource not found")

    response = client.get("/test-http-error")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
    assert response.json()["error"]["message"] == "Resource not found"


def test_validation_error_uses_consistent_response(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    @app.get("/test-validation")
    async def test_validation(required_number: int) -> dict[str, int]:
        return {"required_number": required_number}

    response = client.get("/test-validation", params={"required_number": "not-a-number"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unexpected_error_hides_internal_details(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/test-unexpected")
    async def test_unexpected() -> None:
        raise RuntimeError("sensitive internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert "sensitive internal detail" not in response.text

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.core.logging import JsonFormatter
from app.core.observability import InMemoryMetricsService, configure_sentry, record_event
from app.core.redaction import redact_sensitive
from app.main import create_app


def test_redaction_utility_removes_sensitive_observability_values() -> None:
    payload = {
        "authorization": "Bearer access-token",
        "nested": {
            "ocr_text": "raw medication label text",
            "upload_url": "https://storage.example/upload",
        },
        "items": [{"push_token": "ExponentPushToken[value]"}],
    }

    assert redact_sensitive(payload) == {
        "authorization": "[REDACTED]",
        "nested": {"ocr_text": "[REDACTED]", "upload_url": "[REDACTED]"},
        "items": [{"push_token": "[REDACTED]"}],
    }


def test_json_logging_redacts_sensitive_extra_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("medguide", logging.INFO, __file__, 1, "event", (), None)
    record.ocr_text = "do not log raw OCR"
    record.authorization = "Bearer access-token"

    payload = json.loads(formatter.format(record))

    assert payload["ocr_text"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"


def test_request_id_middleware_uses_supplied_valid_request_id(client: TestClient) -> None:
    request_id = "11111111-1111-4111-8111-111111111111"

    response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_error_handler_does_not_leak_stack_trace_in_production() -> None:
    app = create_app(production_observability_settings())

    @app.get("/unexpected-production-error")
    async def unexpected_production_error() -> None:
        raise RuntimeError("raw medication label text should not leak")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-production-error")

    assert response.status_code == 500
    assert response.json()["error"]["message"] == "An unexpected error occurred"
    assert "Traceback" not in response.text
    assert "raw medication label text should not leak" not in response.text


def test_observability_config_missing_does_not_break_local_development() -> None:
    settings = Settings(app_env=Environment.LOCAL)

    assert configure_sentry(settings) is False


def test_metrics_service_records_and_exposes_safe_event_counts(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    metrics = app.state.metrics
    assert isinstance(metrics, InMemoryMetricsService)

    record_event(
        metrics,
        "ai_scan_completed",
        tags={"result": "LABEL_READ"},
        metadata={"ocr_text": "raw label text is redacted"},
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["counters"] == {"ai_scan_completed|result=LABEL_READ": 1}


def production_observability_settings() -> Settings:
    return Settings(
        app_env=Environment.PRODUCTION,
        database_url="postgresql+asyncpg://user:secret@db.example/medguide",
        redis_url="rediss://user:secret@cache.example/0",
        api_cors_origins=["https://app.example"],
        jwt_secret="a-production-jwt-secret-that-is-long-enough",
        storage_provider="s3",
        s3_bucket="private-medguide-prod-images",
        s3_region="us-east-1",
        s3_access_key_id="prod-s3-access-key",
        s3_secret_access_key="prod-s3-secret-key",
        ocr_provider="aws_textract",
        aws_textract_region="us-east-1",
        aws_textract_access_key_id="prod-textract-access-key",
        aws_textract_secret_access_key="prod-textract-secret-key",
        vision_provider="aws_rekognition",
        aws_rekognition_region="us-east-1",
        aws_rekognition_access_key_id="prod-rekognition-access-key",
        aws_rekognition_secret_access_key="prod-rekognition-secret-key",
        notification_provider="expo",
        expo_push_access_token="prod-expo-push-access-token",
        sentry_dsn=None,
    )

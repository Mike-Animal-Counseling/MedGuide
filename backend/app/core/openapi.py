from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas.errors import ErrorResponse

ERROR_STATUSES = ("400", "401", "403", "404", "409", "422", "500", "503")


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            summary="Production API contract for MedGuide AI.",
            description=app.description,
            routes=app.routes,
            tags=_tags_metadata(),
        )
        _attach_standard_error_responses(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _attach_standard_error_responses(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas.setdefault(
        "ErrorResponse",
        ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}"),
    )
    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, Mapping):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            for status_code in ERROR_STATUSES:
                if status_code in responses:
                    responses[status_code]["content"] = {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                        }
                    }


def _tags_metadata() -> list[dict[str, str]]:
    return [
        {"name": "operations", "description": "Liveness and dependency readiness checks."},
        {"name": "authentication", "description": "Email/password auth and JWT token lifecycle."},
        {"name": "users", "description": "Authenticated user profile management."},
        {"name": "medications", "description": "User-confirmed medication records."},
        {"name": "schedules", "description": "Medication schedule definitions."},
        {"name": "dose logs", "description": "Generated dose occurrences and status changes."},
        {
            "name": "caregivers",
            "description": "Caregiver invitations, links, and linked-patient access.",
        },
        {
            "name": "uploads",
            "description": "Private image signed upload, read, and delete operations.",
        },
        {"name": "AI assistance", "description": "Safety-first OCR and verification assistance."},
        {"name": "devices", "description": "Expo push device registration and removal."},
        {"name": "privacy", "description": "User privacy export and revocation controls."},
    ]

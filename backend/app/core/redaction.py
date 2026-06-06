from collections.abc import Mapping, Sequence
from typing import Any, cast

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "access_token",
        "refresh_token",
        "token",
        "invite_token",
        "password",
        "password_hash",
        "jwt",
        "secret",
        "api_key",
        "ocr_text",
        "raw_ocr_text",
        "push_token",
        "signed_url",
        "upload_url",
        "read_url",
    }
)
REDACTED = "[REDACTED]"


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                redacted[key_text] = REDACTED
            else:
                redacted[key_text] = redact_sensitive(item)
        return redacted
    if isinstance(value, str):
        if _looks_like_bearer(value):
            return REDACTED
        return value
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | str):
        return [redact_sensitive(item) for item in value]
    return value


def safe_audit_metadata(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return cast(dict[str, Any], redact_sensitive(dict(value or {})))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return any(marker in normalized for marker in SENSITIVE_KEYS)


def _looks_like_bearer(value: str) -> bool:
    return value.casefold().startswith("bearer ")

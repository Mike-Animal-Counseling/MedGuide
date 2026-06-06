import importlib
import logging
from collections import Counter
from typing import Any, Literal, Protocol, runtime_checkable

from app.core.config import Settings
from app.core.redaction import redact_sensitive

logger = logging.getLogger(__name__)

ObservabilityEvent = Literal[
    "reminder_sent",
    "dose_confirmed",
    "dose_missed",
    "ai_scan_completed",
    "ai_verify_completed",
    "caregiver_escalation_sent",
    "notification_failed",
]


@runtime_checkable
class MetricsService(Protocol):
    def increment(
        self,
        event: ObservabilityEvent,
        *,
        tags: dict[str, str] | None = None,
        count: int = 1,
    ) -> None: ...

    def snapshot(self) -> dict[str, int]: ...


class InMemoryMetricsService:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def increment(
        self,
        event: ObservabilityEvent,
        *,
        tags: dict[str, str] | None = None,
        count: int = 1,
    ) -> None:
        self._counters[_metric_key(event, tags)] += count

    def snapshot(self) -> dict[str, int]:
        return dict(sorted(self._counters.items()))


class NullMetricsService:
    def increment(
        self,
        event: ObservabilityEvent,
        *,
        tags: dict[str, str] | None = None,
        count: int = 1,
    ) -> None:
        return None

    def snapshot(self) -> dict[str, int]:
        return {}


def configure_sentry(settings: Settings) -> bool:
    if settings.sentry_dsn is None:
        logger.info("Sentry disabled", extra={"observability": "sentry", "enabled": False})
        return False

    try:
        sentry_sdk = importlib.import_module("sentry_sdk")
        integrations = importlib.import_module("sentry_sdk.integrations.fastapi")
        fastapi_integration = integrations.FastApiIntegration()
    except (ImportError, AttributeError) as exc:
        raise RuntimeError("Sentry DSN is configured but sentry-sdk is not installed") from exc

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.sentry_environment or settings.app_env.value,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[fastapi_integration],
        send_default_pii=False,
    )
    logger.info("Sentry enabled", extra={"observability": "sentry", "enabled": True})
    return True


def record_event(
    metrics: MetricsService,
    event: ObservabilityEvent,
    *,
    tags: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    metrics.increment(event, tags=tags)
    logger.info(
        "Observability event recorded",
        extra={
            "event_name": event,
            "event_tags": tags or {},
            "event_metadata": redact_sensitive(metadata or {}),
        },
    )


def _metric_key(event: ObservabilityEvent, tags: dict[str, str] | None) -> str:
    if not tags:
        return event
    suffix = ",".join(f"{key}={value}" for key, value in sorted(tags.items()))
    return f"{event}|{suffix}"

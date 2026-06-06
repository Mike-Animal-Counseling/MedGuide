import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.redaction import redact_sensitive

_STANDARD_LOG_FIELDS = set(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_FIELDS and key not in {"message", "asctime"}
            }
        )
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = {"type": record.exc_info[0].__name__}
        return json.dumps(redact_sensitive(payload), default=str, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

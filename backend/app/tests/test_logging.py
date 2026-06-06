import json
import logging
import sys

from app.core.config import Environment, Settings
from app.core.logging import JsonFormatter, configure_logging


def test_json_formatter_emits_structured_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("medguide", logging.INFO, __file__, 1, "Ready", (), None)
    record.request_id = "request-id"

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "Ready"
    assert payload["request_id"] == "request-id"


def test_json_formatter_does_not_emit_raw_exception_message() -> None:
    formatter = JsonFormatter()
    try:
        raise RuntimeError("raw medication label text")
    except RuntimeError:
        record = logging.getLogger("medguide").makeRecord(
            "medguide",
            logging.ERROR,
            __file__,
            1,
            "Unhandled error",
            (),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))

    assert payload["exception"] == {"type": "RuntimeError"}
    assert "raw medication label text" not in json.dumps(payload)


def test_configure_logging_sets_requested_level() -> None:
    configure_logging(Settings(app_env=Environment.TEST, log_level="warning"))

    assert logging.getLogger().level == logging.WARNING

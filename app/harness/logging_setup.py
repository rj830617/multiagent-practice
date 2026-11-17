import json
import logging
import sys
import time

from app.config import settings

_REDACT_KEYS = {"api_key", "apikey", "authorization", "token", "secret"}


def _redact(detail: str | None) -> str | None:
    if not detail:
        return detail
    lowered = detail.lower()
    for key in _REDACT_KEYS:
        if key in lowered:
            return "[redacted: possible secret in log detail]"
    return detail


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }
        for attr in ("run_id", "stage", "status", "duration_ms"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        return json.dumps(payload)


def get_logger(name: str = "research_agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    return logger


logger = get_logger()


def log_event(stage: str, status: str, run_id: str, duration_ms: float | None = None, detail: str | None = None) -> None:
    logger.info(
        detail or f"{stage}:{status}",
        extra={"run_id": run_id, "stage": stage, "status": status, "duration_ms": duration_ms},
    )

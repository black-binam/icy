"""Logging configuration with redaction of sensitive fields."""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from logging.config import dictConfig
from typing import Any, Union

from app.core.config import get_settings

_Replacement = Union[str, Callable[[re.Match[str]], str]]

_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], _Replacement], ...] = (
    (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?)([^"\'&,\s}]+)'), r"\1***"),
    (re.compile(r'(?i)(token["\']?\s*[:=]\s*["\']?)([^"\'&,\s}]+)'), r"\1***"),
    (re.compile(r"(?i)(authorization\s*:\s*)(\S+)"), r"\1***"),
    (
        re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"),
        lambda m: f"{m.group(1)}***{m.group(3)}",
    ),
)


def _redact(text: str) -> str:
    """Apply all redaction rules to a string."""
    out = text
    for pattern, repl in _SENSITIVE_PATTERNS:
        out = pattern.sub(repl, out)
    return out


class RedactionFilter(logging.Filter):
    """Logging filter that redacts passwords / tokens / emails from messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = _redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _redact_value(v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(_redact_value(v) for v in record.args)
        except Exception:  # noqa: BLE001 — logging must never raise
            pass
        return True


def _redact_value(v: Any) -> Any:
    if isinstance(v, str):
        return _redact(v)
    return v


def configure_logging() -> None:
    """Configure the root logger. Idempotent."""
    settings = get_settings()
    level = settings.LOG_LEVEL.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "redact": {"()": RedactionFilter},
            },
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["redact"],
                },
            },
            "root": {"level": level, "handlers": ["console"]},
            "loggers": {
                "uvicorn.access": {"level": level, "handlers": ["console"], "propagate": False},
                "uvicorn.error": {"level": level, "handlers": ["console"], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )

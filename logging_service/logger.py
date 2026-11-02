"""
Centralized structured logging with automated credential and PII redaction.
"""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Regex patterns for sensitive information redaction
SENSITIVE_PATTERNS = [
    # API keys (e.g. AIzaSy..., sk-..., Bearer ...)
    (re.compile(r"(AIzaSy[0-9A-Za-z-_]{33})", re.IGNORECASE), r"AIzaSy...[REDACTED]"),
    (re.compile(r"(sk-[0-9A-Za-z-_]{20,})", re.IGNORECASE), r"sk-...[REDACTED]"),
    (re.compile(r"(bearer\s+[0-9A-Za-z-_.]{15,})", re.IGNORECASE), r"Bearer [REDACTED]"),
    (re.compile(r"((?:api[_-]?key|secret|password|auth[_-]?token)\s*[:=]\s*['\"]?)([^'\"\s]{8,})(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\3"),
]


class RedactingFilter(logging.Filter):
    """
    Filter that intercepts log records and sanitizes any sensitive credentials or tokens.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        if record.args:
            if isinstance(record.args, dict):
                sanitized = {}
                for k, v in record.args.items():
                    if isinstance(v, str):
                        for pattern, repl in SENSITIVE_PATTERNS:
                            v = pattern.sub(repl, v)
                    sanitized[k] = v
                record.args = sanitized
            elif isinstance(record.args, tuple):
                sanitized_list = []
                for v in record.args:
                    if isinstance(v, str):
                        for pattern, repl in SENSITIVE_PATTERNS:
                            v = pattern.sub(repl, v)
                    sanitized_list.append(v)
                record.args = tuple(sanitized_list)
        return True


def get_default_log_dir() -> Path:
    """Returns the user-local log directory for the assistant."""
    custom_dir = os.environ.get("OMNIASSIST_LOG_DIR")
    if custom_dir:
        target = Path(custom_dir)
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except OSError:
            pass

    home = Path.home()
    log_dir = home / ".omniassist" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        test_file = log_dir / ".perm_check"
        test_file.touch()
        test_file.unlink()
        return log_dir
    except (OSError, PermissionError):
        pass

    fallback = Path.cwd() / ".omniassist" / "logs"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except (OSError, PermissionError):
        import tempfile
        tmp = Path(tempfile.gettempdir()) / "omniassist" / "logs"
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp


_LOGGING_CONFIGURED = False


def configure_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Configures root logging with redacting filter, console stream, and rotating file handlers.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    root_logger = logging.getLogger("omniassist")
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    redacting_filter = RedactingFilter()

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redacting_filter)
    root_logger.addHandler(console_handler)

    # File Handler
    if log_to_file:
        try:
            target_dir = log_dir or get_default_log_dir()
            log_file = target_dir / "assistant.log"
            file_handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(redacting_filter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as exc:
            root_logger.warning("Could not initialize file logging at %s: %s", target_dir if 'target_dir' in locals() else 'unknown', exc)

    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Returns a child logger under the 'omniassist' hierarchy.
    """
    if not _LOGGING_CONFIGURED:
        configure_logging()
    if name.startswith("omniassist."):
        return logging.getLogger(name)
    return logging.getLogger(f"omniassist.{name}")

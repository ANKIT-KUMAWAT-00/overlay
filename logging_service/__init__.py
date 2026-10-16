"""
Logging service package for OmniAssist Python Desktop Assistant.
Provides centralized, structured, redaction-safe logging.
"""

from .logger import get_logger, configure_logging, RedactingFilter

__all__ = ["get_logger", "configure_logging", "RedactingFilter"]

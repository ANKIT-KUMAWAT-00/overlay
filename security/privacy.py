"""
Privacy filters, PII sanitization, and prompt injection defense.
"""

from __future__ import annotations

import re
from typing import Tuple, List

from logging_service.logger import get_logger

logger = get_logger("security.privacy")

# Patterns for sensitive user information
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
AUTH_BEARER_REGEX = re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9_\-\.]{20,})\b")
PRIVATE_KEY_BLOCK_REGEX = re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----")

# Detection of potential adversarial prompt injection payloads
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)system\s*prompt\s*override"),
    re.compile(r"(?i)you\s+are\s+now\s+in\s+developer\s+mode"),
    re.compile(r"(?i)bypass\s+(all\s+)?safety\s+filters"),
]


class PrivacyFilter:
    """
    Scans and sanitizes captured question context prior to external AI transmission.
    """

    def __init__(
        self,
        redact_pii: bool = True,
        detect_injections: bool = True,
        redact_keys: bool = True,
    ) -> None:
        self.redact_pii = redact_pii
        self.detect_injections = detect_injections
        self.redact_keys = redact_keys

    def sanitize(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitizes text and returns (sanitized_text, warnings_list).
        """
        if not text:
            return "", []

        warnings = []
        cleaned = text

        if self.detect_injections:
            for pattern in PROMPT_INJECTION_PATTERNS:
                if pattern.search(cleaned):
                    warnings.append(f"Potential prompt injection pattern detected: '{pattern.pattern}'")
                    logger.warning("Prompt injection signature flagged in captured text.")

        if self.redact_keys:
            if PRIVATE_KEY_BLOCK_REGEX.search(cleaned):
                cleaned = PRIVATE_KEY_BLOCK_REGEX.sub("[REDACTED_PRIVATE_KEY]", cleaned)
                warnings.append("Private key block redacted from input.")
            if AUTH_BEARER_REGEX.search(cleaned):
                cleaned = AUTH_BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", cleaned)
                warnings.append("Auth token redacted from input.")

        if self.redact_pii:
            if CREDIT_CARD_REGEX.search(cleaned):
                cleaned = CREDIT_CARD_REGEX.sub("[REDACTED_CARD_NUMBER]", cleaned)
                warnings.append("Payment card number redacted.")
            if SSN_REGEX.search(cleaned):
                cleaned = SSN_REGEX.sub("[REDACTED_SSN]", cleaned)
                warnings.append("Social security number redacted.")

        return cleaned, warnings


def sanitize_for_prompt(text: str) -> str:
    """Convenience helper to quickly scrub a string using default privacy rules."""
    sanitizer = PrivacyFilter()
    sanitized, _ = sanitizer.sanitize(text)
    return sanitized

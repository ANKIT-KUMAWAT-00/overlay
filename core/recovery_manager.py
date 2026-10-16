"""
Standardized error classification, bounded backoff, and state-preserving recovery policies.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Callable

from logging_service.logger import get_logger

logger = get_logger("core.recovery_manager")


class ErrorCategory(str, Enum):
    """15 Standardized error classifications."""
    AUTH_FAILED = "AUTH_FAILED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    PROMPT_BLOCKED = "PROMPT_BLOCKED"
    CAPTURE_EMPTY = "CAPTURE_EMPTY"
    CAPTURE_PERMISSION_DENIED = "CAPTURE_PERMISSION_DENIED"
    WINDOW_MISMATCH = "WINDOW_MISMATCH"
    INSERTION_FAILED = "INSERTION_FAILED"
    SYNTAX_INVALID = "SYNTAX_INVALID"
    TRUNCATED_RESPONSE = "TRUNCATED_RESPONSE"
    CLIPBOARD_LOCKED = "CLIPBOARD_LOCKED"
    SHORTCUT_CONFLICT = "SHORTCUT_CONFLICT"
    UNEXPECTED_INTERNAL_ERROR = "UNEXPECTED_INTERNAL_ERROR"


class RecoveryAction(str, Enum):
    """Recommended next action for recovery."""
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    OPEN_SETTINGS = "OPEN_SETTINGS"
    FALLBACK_TO_MANUAL = "FALLBACK_TO_MANUAL"
    FALLBACK_TO_CLIPBOARD = "FALLBACK_TO_CLIPBOARD"
    DISPLAY_IN_HUD = "DISPLAY_IN_HUD"
    ABORT = "ABORT"


@dataclass
class PreservedWorkState:
    """Stores work completed prior to failure to ensure zero data loss."""
    captured_text: Optional[str] = None
    captured_image_bytes: Optional[bytes] = None
    target_app: Optional[str] = None
    generated_answer: Optional[str] = None
    validation_warnings: list[str] = field(default_factory=list)


@dataclass
class RecoveryPlan:
    """Prescribed remediation for an encountered failure."""
    category: ErrorCategory
    action: RecoveryAction
    user_message: str
    is_retryable: bool
    backoff_delay_sec: float = 0.0
    suggested_fix: str = ""


class RecoveryManager:
    """
    Classifies application failures and generates actionable recovery plans
    while safeguarding user work from being lost.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.retry_counts: Dict[str, int] = {}
        self.preserved_state = PreservedWorkState()

    def preserve_work(
        self,
        captured_text: Optional[str] = None,
        captured_image_bytes: Optional[bytes] = None,
        target_app: Optional[str] = None,
        generated_answer: Optional[str] = None,
    ) -> None:
        """Stores in-progress artifacts."""
        if captured_text is not None:
            self.preserved_state.captured_text = captured_text
        if captured_image_bytes is not None:
            self.preserved_state.captured_image_bytes = captured_image_bytes
        if target_app is not None:
            self.preserved_state.target_app = target_app
        if generated_answer is not None:
            self.preserved_state.generated_answer = generated_answer

    def clear_preserved_work(self) -> None:
        """Resets saved state upon successful completion."""
        self.preserved_state = PreservedWorkState()
        self.retry_counts.clear()

    def classify_error(self, exc: Exception) -> ErrorCategory:
        """Maps arbitrary Python exceptions to standardized ErrorCategory."""
        msg = str(exc).lower()

        # Auth
        if "api_key" in msg or "unauthenticated" in msg or "401" in msg or "invalid api key" in msg:
            return ErrorCategory.AUTH_FAILED

        # Quota / Rate limit
        if "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg:
            return ErrorCategory.QUOTA_EXCEEDED

        # Network timeout
        if "timeout" in msg or "deadline" in msg:
            return ErrorCategory.NETWORK_TIMEOUT

        # Network offline
        if "nodename nor servname" in msg or "connection refused" in msg or "network is unreachable" in msg:
            return ErrorCategory.NETWORK_UNAVAILABLE

        # Model unavailable
        if "503" in msg or "500" in msg or "service unavailable" in msg:
            return ErrorCategory.MODEL_UNAVAILABLE

        # Safety block
        if "safety" in msg or "blocked" in msg or "content policy" in msg:
            return ErrorCategory.PROMPT_BLOCKED

        # Permissions
        if "permission" in msg or "accessibility" in msg or "axisprocesstrusted" in msg:
            return ErrorCategory.CAPTURE_PERMISSION_DENIED

        # Target window mismatch
        if "target application mismatch" in msg or "window mismatch" in msg:
            return ErrorCategory.WINDOW_MISMATCH

        # Insertion failure
        if "insertion failed" in msg or "paste injection failed" in msg:
            return ErrorCategory.INSERTION_FAILED

        # Syntax or Truncation
        if "json validation failed" in msg:
            return ErrorCategory.SYNTAX_INVALID
        if "truncated" in msg:
            return ErrorCategory.TRUNCATED_RESPONSE

        # Shortcut conflicts
        if "hotkey" in msg or "shortcut" in msg or "already registered" in msg:
            return ErrorCategory.SHORTCUT_CONFLICT

        return ErrorCategory.UNEXPECTED_INTERNAL_ERROR

    def create_recovery_plan(self, exc: Exception, operation_key: str = "default") -> RecoveryPlan:
        """
        Formulates a concrete recovery strategy based on error category and retry history.
        """
        category = self.classify_error(exc)
        current_retries = self.retry_counts.get(operation_key, 0)

        # 1. Auth Failures: Non-retryable without user intervention
        if category == ErrorCategory.AUTH_FAILED:
            return RecoveryPlan(
                category=category,
                action=RecoveryAction.OPEN_SETTINGS,
                user_message="Gemini API Key is invalid or unconfigured.",
                is_retryable=False,
                suggested_fix="Please open Settings and provide a valid Google Gemini API Key.",
            )

        # 2. Rate Limits & Quotas: Retryable with exponential backoff
        if category in (ErrorCategory.QUOTA_EXCEEDED, ErrorCategory.NETWORK_TIMEOUT, ErrorCategory.MODEL_UNAVAILABLE):
            if current_retries < self.max_retries:
                delay = (2.0 ** current_retries) + random.uniform(0.2, 0.8)
                self.retry_counts[operation_key] = current_retries + 1
                return RecoveryPlan(
                    category=category,
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    user_message=f"Gemini API is busy or timed out. Retrying in {delay:.1f}s...",
                    is_retryable=True,
                    backoff_delay_sec=delay,
                    suggested_fix="Temporary network/quota backoff in progress.",
                )
            else:
                return RecoveryPlan(
                    category=category,
                    action=RecoveryAction.DISPLAY_IN_HUD,
                    user_message="Gemini API request failed after multiple retries.",
                    is_retryable=False,
                    suggested_fix="Check your internet connection and API quota at Google AI Studio.",
                )

        # 3. Capture failures
        if category == ErrorCategory.CAPTURE_EMPTY:
            return RecoveryPlan(
                category=category,
                action=RecoveryAction.FALLBACK_TO_MANUAL,
                user_message="No selected text found in the active window.",
                is_retryable=False,
                suggested_fix="Select text in your target application or enter your prompt in the HUD.",
            )

        # 4. Accessibility permissions
        if category == ErrorCategory.CAPTURE_PERMISSION_DENIED:
            return RecoveryPlan(
                category=category,
                action=RecoveryAction.FALLBACK_TO_MANUAL,
                user_message="OS Accessibility permission is required for reading active text.",
                is_retryable=False,
                suggested_fix="Enable Accessibility permissions for OmniAssist in OS System Settings.",
            )

        # 5. Insertion Failures: Fall back to clipboard & HUD
        if category in (ErrorCategory.INSERTION_FAILED, ErrorCategory.WINDOW_MISMATCH):
            return RecoveryPlan(
                category=category,
                action=RecoveryAction.FALLBACK_TO_CLIPBOARD,
                user_message="Could not inject text directly into target window (focus changed).",
                is_retryable=False,
                suggested_fix="Your answer was safely copied to the clipboard. Paste it using Cmd+V / Ctrl+V.",
            )

        # 6. Syntax or truncation
        if category in (ErrorCategory.SYNTAX_INVALID, ErrorCategory.TRUNCATED_RESPONSE):
            return RecoveryPlan(
                category=category,
                action=RecoveryAction.DISPLAY_IN_HUD,
                user_message="Answer received, but had minor formatting or truncation issues.",
                is_retryable=False,
                suggested_fix="Review and edit the answer in the HUD before copying.",
            )

        # Default fallback
        return RecoveryPlan(
            category=category,
            action=RecoveryAction.DISPLAY_IN_HUD,
            user_message=f"Operation notice: {exc}",
            is_retryable=False,
            suggested_fix="You can view and copy the generated answer from the HUD window.",
        )

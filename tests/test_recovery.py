"""
Unit tests for recovery manager, error categorization, and work preservation.
"""

import pytest
from core.recovery_manager import (
    RecoveryManager,
    ErrorCategory,
    RecoveryAction,
    PreservedWorkState,
)


def test_error_classification():
    rm = RecoveryManager()

    # Auth
    assert rm.classify_error(Exception("Invalid API key provided")) == ErrorCategory.AUTH_FAILED
    # Quota
    assert rm.classify_error(Exception("429 Resource Exhausted: Quota exceeded")) == ErrorCategory.QUOTA_EXCEEDED
    # Timeout
    assert rm.classify_error(Exception("Connection timeout")) == ErrorCategory.NETWORK_TIMEOUT
    # Permissions
    assert rm.classify_error(Exception("Accessibility permission required")) == ErrorCategory.CAPTURE_PERMISSION_DENIED
    # Mismatch
    assert rm.classify_error(Exception("Target application mismatch")) == ErrorCategory.WINDOW_MISMATCH
    # Insertion
    assert rm.classify_error(Exception("Paste injection failed")) == ErrorCategory.INSERTION_FAILED


def test_recovery_plan_auth_failure():
    rm = RecoveryManager()
    plan = rm.create_recovery_plan(Exception("Invalid API Key"))
    assert plan.category == ErrorCategory.AUTH_FAILED
    assert plan.action == RecoveryAction.OPEN_SETTINGS
    assert not plan.is_retryable


def test_recovery_plan_rate_limit_backoff():
    rm = RecoveryManager(max_retries=2)
    plan = rm.create_recovery_plan(Exception("429 rate limit exceeded"), operation_key="gemini_call")
    assert plan.category == ErrorCategory.QUOTA_EXCEEDED
    assert plan.action == RecoveryAction.RETRY_WITH_BACKOFF
    assert plan.is_retryable
    assert plan.backoff_delay_sec > 0.0


def test_work_preservation_across_failures():
    rm = RecoveryManager()
    
    # Capture succeeds
    rm.preserve_work(captured_text="def solve(x): return x * 2", target_app="VS Code")
    assert isinstance(rm.preserved_state, PreservedWorkState)
    assert rm.preserved_state.captured_text == "def solve(x): return x * 2"
    assert rm.preserved_state.target_app == "VS Code"

    # AI generation succeeds
    rm.preserve_work(generated_answer="42")
    assert rm.preserved_state.generated_answer == "42"

    # Preserved state persists when recovery plan created
    plan = rm.create_recovery_plan(Exception("Paste injection failed"))
    assert plan.category == ErrorCategory.INSERTION_FAILED
    assert rm.preserved_state.generated_answer == "42"

    # Clear work on completion
    rm.clear_preserved_work()
    assert rm.preserved_state.generated_answer is None

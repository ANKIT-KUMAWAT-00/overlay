"""
Abstract base interface and structured response models for AI providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List


class OutputFormat(str, Enum):
    """Target output format modes."""
    AUTO = "auto"
    CODE = "code"
    MULTIPLE_CHOICE = "multiple_choice"
    THEORY = "theory"
    JSON = "json"
    SHORT_ANSWER = "short_answer"
    PARAGRAPH = "paragraph"


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AIResponse:
    """Structured response container from an AI provider."""
    text: str
    model: str
    finish_reason: str = "STOP"
    output_format: OutputFormat = OutputFormat.AUTO
    token_usage: Optional[TokenUsage] = None
    latency_ms: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None
    is_success: bool = True
    error_message: Optional[str] = None


class AIError(Exception):
    """Domain exception for AI provider operations."""

    def __init__(
        self,
        message: str,
        category: str = "generic",
        retryable: bool = False,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category  # 'auth', 'quota', 'rate_limit', 'network', 'invalid_request', 'timeout'
        self.retryable = retryable
        self.status_code = status_code


class AIProvider(ABC):
    """
    Abstract interface for AI intelligence backends.
    Allows seamlessly plugging in Gemini, self-hosted LLMs, or alternative providers.
    """

    @abstractmethod
    def generate_answer(
        self,
        prompt: str,
        context: Optional[str] = None,
        target_app_name: Optional[str] = None,
        format_preference: OutputFormat = OutputFormat.AUTO,
        image_bytes: Optional[bytes] = None,
        image_mime_type: str = "image/png",
    ) -> AIResponse:
        """
        Generates an answer based on prompt, optional context, and optional visual input.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if provider credentials and network connectivity are operational."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the configured model name."""
        pass

    def set_model(self, model_name: str) -> None:
        """Updates the active model identifier."""
        pass

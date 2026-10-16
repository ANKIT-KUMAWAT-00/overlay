"""
Google Gemini AI provider using official google-genai SDK.
Implements bounded retries, rate-limit recovery, and multimodal vision inputs.
"""

from __future__ import annotations

import random
import time
from typing import Optional

from ai.provider import AIProvider, AIResponse, AIError, OutputFormat, TokenUsage
from ai.prompt_builder import PromptBuilder
from security.credential_store import CredentialStore
from logging_service.logger import get_logger

logger = get_logger("ai.gemini_provider")


class GeminiProvider(AIProvider):
    """
    Official Google Gemini API provider implementation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-flash-preview",
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        credential_store: Optional[CredentialStore] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self._model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        self.cred_store = credential_store or CredentialStore()
        self.prompt_builder = prompt_builder or PromptBuilder()

        self._api_key = api_key or self.cred_store.get_api_key()
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initializes google.genai.Client if key is available."""
        if not self._api_key:
            self._api_key = self.cred_store.get_api_key()

        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
                logger.info("Initialized Gemini Client with model %s", self._model_name)
            except Exception as exc:
                logger.error("Failed to initialize google-genai client: %s", exc)
                self._client = None
        else:
            logger.warning("No Gemini API key available during initialization.")

    @property
    def model_name(self) -> str:
        return self._model_name

    def set_api_key(self, api_key: str) -> None:
        """Dynamically updates API key."""
        self._api_key = api_key.strip()
        self._initialize_client()

    def set_model(self, model_name: str) -> None:
        """Updates model identifier."""
        self._model_name = model_name
        logger.info("Switched active Gemini model to %s", model_name)

    def health_check(self) -> bool:
        """Quick connectivity probe."""
        if not self._api_key or not self._client:
            return False
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=10,
            )
            resp = self._client.models.generate_content(
                model=self._model_name,
                contents="ping",
                config=config,
            )
            return bool(resp and resp.text)
        except Exception as exc:
            logger.warning("Gemini health check probe failed: %s", exc)
            return False

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
        Submits prompt with bounded retry and exponential backoff.
        """
        if not self._api_key:
            # Recheck credential store in case key was added via Settings
            self._api_key = self.cred_store.get_api_key()
            self._initialize_client()

        if not self._api_key or not self._client:
            raise AIError(
                message="Gemini API Key is not configured. Please open Settings to set your API key.",
                category="auth",
                retryable=False,
            )

        assembled_prompt, effective_format = self.prompt_builder.assemble_user_prompt(
            question=prompt,
            context=context,
            target_app=target_app_name,
            format_preference=format_preference,
        )

        system_instruction = self.prompt_builder.build_system_instruction(
            format_preference=effective_format,
            target_app=target_app_name,
        )

        # Prepare multimodal or text contents
        from google.genai import types

        contents = []
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type))
        contents.append(assembled_prompt)

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            system_instruction=system_instruction,
        )

        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Submitting request to Gemini (attempt %d/%d, model=%s)",
                    attempt + 1,
                    self.max_retries + 1,
                    self._model_name,
                )
                resp = self._client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=config,
                )

                latency = (time.perf_counter() - start_time) * 1000.0
                text = resp.text or ""

                # Extract token usage if returned by SDK
                token_usage = TokenUsage()
                if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                    token_usage.prompt_tokens = getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
                    token_usage.candidate_tokens = getattr(resp.usage_metadata, "candidates_token_count", 0) or 0
                    token_usage.total_tokens = getattr(resp.usage_metadata, "total_token_count", 0) or 0

                finish_reason = "STOP"
                if hasattr(resp, "candidates") and resp.candidates:
                    c = resp.candidates[0]
                    if hasattr(c, "finish_reason") and c.finish_reason:
                        finish_reason = str(c.finish_reason)

                return AIResponse(
                    text=text,
                    model=self._model_name,
                    finish_reason=finish_reason,
                    output_format=effective_format,
                    token_usage=token_usage,
                    latency_ms=latency,
                    is_success=True,
                )

            except Exception as exc:
                last_error = exc
                ai_err = self._classify_error(exc)
                logger.warning(
                    "Gemini API request failed on attempt %d: [%s] %s",
                    attempt + 1,
                    ai_err.category,
                    ai_err.message,
                )

                if not ai_err.retryable or attempt >= self.max_retries:
                    raise ai_err

                # Exponential backoff with jitter
                backoff = (2.0 ** attempt) + random.uniform(0.1, 0.8)
                logger.info("Backing off for %.2f seconds before retry...", backoff)
                time.sleep(backoff)

        raise AIError(
            message=f"Gemini generation failed after {self.max_retries} retries: {last_error}",
            category="network",
            retryable=False,
        )

    def _classify_error(self, exc: Exception) -> AIError:
        """Translates SDK exceptions into structured domain AIError."""
        msg = str(exc)
        lowered = msg.lower()

        # Auth
        if "api_key" in lowered or "unauthenticated" in lowered or "invalid api key" in lowered or "401" in lowered:
            return AIError(
                message="Invalid or missing Gemini API key. Please check your credentials.",
                category="auth",
                retryable=False,
                status_code=401,
            )
        # Quota / Rate limit
        if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
            return AIError(
                message="Gemini API rate limit or quota exceeded. Retrying shortly.",
                category="quota",
                retryable=True,
                status_code=429,
            )
        # Timeout
        if "timeout" in lowered or "deadline" in lowered:
            return AIError(
                message="Gemini API request timed out.",
                category="timeout",
                retryable=True,
                status_code=504,
            )
        # Server errors (500, 503)
        if "500" in lowered or "503" in lowered or "internal" in lowered or "unavailable" in lowered:
            return AIError(
                message="Gemini server temporary error. Retrying...",
                category="network",
                retryable=True,
                status_code=500,
            )

        return AIError(
            message=f"Gemini API error: {msg}",
            category="generic",
            retryable=False,
        )

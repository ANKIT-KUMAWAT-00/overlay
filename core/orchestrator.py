"""
Central workflow orchestrator bridging Capture, AI Reasoning, Validation, and Delivery.
"""

from __future__ import annotations

import threading
from typing import Optional, Callable

from capture.question_capture import QuestionCaptureService, CapturedQuestion, CaptureMethod
from capture.screen_capture import ScreenRegion
from ai.provider import AIProvider, AIResponse, OutputFormat
from ai.gemini_provider import GeminiProvider
from ai.response_validator import ResponseValidator, ValidationResult
from delivery.answer_delivery import AnswerDeliveryCoordinator, DeliveryResult
from core.application_detector import ApplicationDetector
from core.capability_registry import CapabilityRegistry
from core.recovery_manager import RecoveryManager, RecoveryPlan
from config.settings import AppSettings, get_settings
from logging_service.logger import get_logger

logger = get_logger("core.orchestrator")


class AssistantOrchestrator:
    """
    Main stateful business logic controller.
    Runs non-blocking interaction pipelines in background threads.
    """

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        capture_service: Optional[QuestionCaptureService] = None,
        delivery_coordinator: Optional[AnswerDeliveryCoordinator] = None,
        settings: Optional[AppSettings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.ai_provider = ai_provider or GeminiProvider(
            model_name=self.settings.ai.model_name,
            temperature=self.settings.ai.temperature,
            max_output_tokens=self.settings.ai.max_output_tokens,
            timeout_seconds=self.settings.ai.timeout_seconds,
            max_retries=self.settings.ai.max_retries,
            ssl_verify=self.settings.ai.ssl_verify,
        )
        self.capture_service = capture_service or QuestionCaptureService()
        self.delivery_coordinator = delivery_coordinator or AnswerDeliveryCoordinator(settings=self.settings)
        self.app_detector = ApplicationDetector()
        self.capability_registry = CapabilityRegistry()
        self.recovery_manager = RecoveryManager()
        self.validator = ResponseValidator()
        self.last_generated_answer: Optional[str] = None

        # Cancellation flag
        self._cancel_requested = threading.Event()
        self._current_thread: Optional[threading.Thread] = None

        # Callback hooks for UI / Event listeners
        self.on_status_update: Optional[Callable[[str], None]] = None
        self.on_question_captured: Optional[Callable[[CapturedQuestion], None]] = None
        self.on_answer_ready: Optional[Callable[[str, ValidationResult], None]] = None
        self.on_delivery_finished: Optional[Callable[[DeliveryResult], None]] = None
        self.on_recovery_triggered: Optional[Callable[[RecoveryPlan], None]] = None

    def cancel(self) -> None:
        """Signals active interaction pipeline to abort immediately."""
        logger.info("Cancellation requested by user.")
        self._cancel_requested.set()

    def run_interaction_async(
        self,
        method: CaptureMethod = CaptureMethod.SMART,
        region: Optional[ScreenRegion] = None,
        manual_prompt: Optional[str] = None,
        format_preference: OutputFormat = OutputFormat.AUTO,
        include_vision: bool = True,
        image_bytes: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg",
    ) -> threading.Thread:
        """
        Launches interaction asynchronously in a background worker thread.
        Prevents blocking the GUI event loop.
        """
        self._cancel_requested.clear()
        thread = threading.Thread(
            target=self._run_pipeline,
            args=(method, region, manual_prompt, format_preference, include_vision, image_bytes, image_mime_type),
            name="OrchestratorWorker",
            daemon=True,
        )
        self._current_thread = thread
        thread.start()
        return thread

    def _notify_status(self, message: str) -> None:
        logger.info("[Status] %s", message)
        if self.on_status_update:
            try:
                self.on_status_update(message)
            except Exception as exc:
                logger.warning("Status callback error: %s", exc)

    def _run_pipeline(
        self,
        method: CaptureMethod,
        region: Optional[ScreenRegion],
        manual_prompt: Optional[str],
        format_preference: OutputFormat,
        include_vision: bool = True,
        image_bytes: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg",
    ) -> None:
        try:
            self._notify_status("Detecting active application...")
            active_app = self.app_detector.detect_active_application()
            caps = self.capability_registry.get_capabilities(active_app.category)

            # Auto-infer format preference if code editor detected
            if format_preference == OutputFormat.AUTO and caps.prefers_raw_code:
                format_preference = OutputFormat.CODE

            if self._cancel_requested.is_set():
                self._notify_status("Interaction cancelled.")
                return

            # Step 1: Question Capture
            self._notify_status(f"Capturing question context from {active_app.name}...")
            if image_bytes is not None and len(image_bytes) > 0:
                prompt_text = (
                    manual_prompt.strip()
                    if (manual_prompt and manual_prompt.strip())
                    else (
                        "Carefully read and analyze the screen. If this is a coding problem or task: detect the "
                        "intended programming language from the question, code editor stub, or instructions "
                        "(e.g. C++, Java, Python, JavaScript, Go, etc. - especially check if C++ / cpp is requested "
                        "or provided in the starter template), and output ONLY the complete, working code solution "
                        "in that exact language ready to be executed/compiled (omit problem analysis, explanation essays, "
                        "and complexity analysis). If it is a multiple choice or other task, give the exact direct answer."
                    )
                )
                captured = CapturedQuestion(
                    text=prompt_text,
                    method=CaptureMethod.FULLSCREEN_VISION,
                    source_app=active_app.name,
                    window_title=active_app.window_title,
                    image_bytes=image_bytes,
                    image_mime_type=image_mime_type,
                )
            elif manual_prompt and manual_prompt.strip():
                captured = CapturedQuestion(
                    text=manual_prompt.strip(),
                    method=CaptureMethod.MANUAL,
                    source_app=active_app.name,
                    window_title=active_app.window_title,
                )
            else:
                captured = self.capture_service.capture(
                    method=method,
                    region=region,
                    include_vision=include_vision,
                )

            self.recovery_manager.preserve_work(
                captured_text=captured.text,
                captured_image_bytes=captured.image_bytes,
                target_app=active_app.name,
            )

            if self.on_question_captured:
                self.on_question_captured(captured)

            if not captured.has_content:
                raise ValueError("No question or context could be extracted.")

            if self._cancel_requested.is_set():
                self._notify_status("Interaction cancelled.")
                return

            # Step 2: AI Generation
            self._notify_status(f"Generating solution via {self.ai_provider.model_name}...")
            ai_resp: AIResponse = self.ai_provider.generate_answer(
                prompt=captured.text,
                context=None,
                target_app_name=active_app.name,
                format_preference=format_preference,
                image_bytes=captured.image_bytes,
                image_mime_type=captured.image_mime_type,
            )

            if self._cancel_requested.is_set():
                self._notify_status("Interaction cancelled.")
                return

            # Step 3: Response Validation & Auto-Correction
            self._notify_status("Validating syntax and response completeness...")
            val_result = self.validator.validate(
                text=ai_resp.text,
                expected_format=ai_resp.output_format,
                finish_reason=ai_resp.finish_reason,
            )

            final_answer = val_result.corrected_text
            self.last_generated_answer = final_answer
            self.recovery_manager.preserve_work(generated_answer=final_answer)

            if self.on_answer_ready:
                self.on_answer_ready(final_answer, val_result)

            if self._cancel_requested.is_set():
                self._notify_status("Interaction cancelled.")
                return

            # Step 4: Answer Delivery
            if self.settings.delivery.auto_copy_to_clipboard or self.settings.delivery.auto_insert_to_active_app:
                self._notify_status("Delivering answer to target workspace...")
                del_result = self.delivery_coordinator.deliver(
                    answer_text=final_answer,
                    target_app=active_app.name,
                    target_title=active_app.window_title,
                )
                if self.on_delivery_finished:
                    self.on_delivery_finished(del_result)

            self._notify_status("Complete.")
            self.recovery_manager.clear_preserved_work()

        except Exception as exc:
            logger.error("Orchestrator pipeline encountered error: %s", exc, exc_info=True)
            plan = self.recovery_manager.create_recovery_plan(exc)
            if self.on_recovery_triggered:
                self.on_recovery_triggered(plan)
            self._notify_status(f"Error: {plan.user_message}")

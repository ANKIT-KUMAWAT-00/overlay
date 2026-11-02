"""
Unified question capture engine orchestrating selection, accessibility, OCR, and vision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from capture.screen_capture import ScreenCaptureService, ScreenRegion
from capture.ocr_engine import OCREngine, OCRResult
from capture.accessibility_capture import AccessibilityCaptureService
from platforms import get_platform_service
from logging_service.logger import get_logger

logger = get_logger("capture.question_capture")


class CaptureMethod(str, Enum):
    """Methods used to capture the question context."""
    SELECTION = "selection"
    ACCESSIBILITY = "accessibility"
    CLIPBOARD = "clipboard"
    OCR_REGION = "ocr_region"
    FULLSCREEN_VISION = "fullscreen_vision"
    MANUAL = "manual"
    SMART = "smart"


@dataclass
class CapturedQuestion:
    """Standardized captured context payload."""
    text: str
    method: CaptureMethod
    source_app: str = "Unknown"
    window_title: str = ""
    image_bytes: Optional[bytes] = None
    image_mime_type: str = "image/png"
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(self.text.strip()) or (self.image_bytes is not None and len(self.image_bytes) > 0)


class QuestionCaptureService:
    """
    Coordinates context extraction across all available OS mechanisms.
    """

    def __init__(
        self,
        screen_capture: Optional[ScreenCaptureService] = None,
        ocr_engine: Optional[OCREngine] = None,
        accessibility: Optional[AccessibilityCaptureService] = None,
        pre_capture_hook: Optional[Callable[[], None]] = None,
    ) -> None:
        self.screen_capture = screen_capture or ScreenCaptureService()
        self.ocr_engine = ocr_engine or OCREngine()
        self.accessibility = accessibility or AccessibilityCaptureService()
        self.platform = get_platform_service()
        self.pre_capture_hook = pre_capture_hook

    def capture(
        self,
        method: CaptureMethod = CaptureMethod.SMART,
        region: Optional[ScreenRegion] = None,
        include_vision: bool = True,
    ) -> CapturedQuestion:
        """
        Executes question capture according to specified or smart cascaded strategy.
        """
        app_info = self.platform.get_active_app_info()
        source_app = app_info.get("app_name", "Unknown")
        window_title = app_info.get("window_title", "")
        warnings: List[str] = []

        logger.info("Initiating capture (method=%s) from app: %s", method, source_app)

        # 1. Direct Selection
        if method in (CaptureMethod.SELECTION, CaptureMethod.SMART):
            selected = self.platform.get_selected_text_via_clipboard()
            if selected and selected.strip():
                logger.info("Successfully captured text via user selection (%d chars)", len(selected))
                return CapturedQuestion(
                    text=selected.strip(),
                    method=CaptureMethod.SELECTION,
                    source_app=source_app,
                    window_title=window_title,
                    confidence=1.0,
                )
            elif method == CaptureMethod.SELECTION:
                warnings.append("No text was selected in the target application.")

        # 2. Accessibility Interface
        if method in (CaptureMethod.ACCESSIBILITY, CaptureMethod.SMART):
            acc_text, role = self.accessibility.capture_focused_text()
            if acc_text and acc_text.strip():
                logger.info("Successfully captured text via Accessibility (%s, %d chars)", role, len(acc_text))
                return CapturedQuestion(
                    text=acc_text.strip(),
                    method=CaptureMethod.ACCESSIBILITY,
                    source_app=source_app,
                    window_title=window_title,
                    confidence=0.9,
                )

        # 3. OCR on screen region or active window
        if method in (CaptureMethod.OCR_REGION, CaptureMethod.SMART) and region:
            try:
                if self.pre_capture_hook:
                    try:
                        self.pre_capture_hook()
                    except Exception as hook_err:
                        logger.warning("pre_capture_hook notice: %s", hook_err)

                img = self.screen_capture.capture_region(region)
                ocr_res = self.ocr_engine.extract_text(img)
                img_bytes = self.screen_capture.image_to_bytes(img) if include_vision else None

                if ocr_res.success and ocr_res.text:
                    logger.info("Successfully captured text via OCR region (%d chars)", len(ocr_res.text))
                    return CapturedQuestion(
                        text=ocr_res.text,
                        method=CaptureMethod.OCR_REGION,
                        source_app=source_app,
                        window_title=window_title,
                        image_bytes=img_bytes,
                        confidence=0.8,
                    )
                else:
                    if ocr_res.error_message:
                        warnings.append(f"OCR Notice: {ocr_res.error_message}")
            except Exception as exc:
                logger.warning("OCR capture encountered error: %s", exc)
                warnings.append(f"Screen region capture error: {exc}")

        # 4. Multimodal Vision Fallback (Captures screen photo when no text selected)
        if method in (CaptureMethod.FULLSCREEN_VISION, CaptureMethod.SMART) and (include_vision or method == CaptureMethod.FULLSCREEN_VISION):
            try:
                if self.pre_capture_hook:
                    try:
                        self.pre_capture_hook()
                    except Exception as hook_err:
                        logger.warning("pre_capture_hook notice: %s", hook_err)

                screenshot = self.screen_capture.capture_fullscreen()
                img_bytes = self.screen_capture.image_to_bytes(screenshot, format="JPEG", quality=80)
                logger.info("Captured fullscreen image for Gemini Vision analysis (%d bytes)", len(img_bytes))
                return CapturedQuestion(
                    text=(
                        "Carefully read and analyze the screen. If this is a coding problem or task: detect the "
                        "intended programming language from the question, code editor stub, or instructions "
                        "(e.g. C++, Java, Python, JavaScript, Go, etc. - especially check if C++ / cpp is requested "
                        "or provided in the starter template), and output ONLY the complete, working code solution "
                        "in that exact language ready to be executed/compiled (omit problem analysis, explanation essays, "
                        "and complexity analysis). If it is a multiple choice or other task, give the exact direct answer."
                    ),
                    method=CaptureMethod.FULLSCREEN_VISION,
                    source_app=source_app,
                    window_title=window_title,
                    image_bytes=img_bytes,
                    image_mime_type="image/jpeg",
                    confidence=0.9,
                    warnings=warnings,
                )
            except Exception as exc:
                logger.warning("Fullscreen vision capture error: %s", exc)
                warnings.append(f"Fullscreen vision capture error: {exc}")

        # 5. Fallback: User-approved Clipboard
        if method == CaptureMethod.CLIPBOARD:
            import pyperclip
            clip_text = pyperclip.paste()
            if clip_text and clip_text.strip():
                return CapturedQuestion(
                    text=clip_text.strip(),
                    method=CaptureMethod.CLIPBOARD,
                    source_app=source_app,
                    window_title=window_title,
                    confidence=0.7,
                )

        # Default blank capture for manual entry
        return CapturedQuestion(
            text="",
            method=CaptureMethod.MANUAL,
            source_app=source_app,
            window_title=window_title,
            confidence=0.5,
            warnings=warnings or ["Could not automatically extract text. Please enter your request manually."],
        )

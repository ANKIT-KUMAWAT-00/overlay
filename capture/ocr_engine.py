"""
OCR engine with image preprocessing, contrast enhancement, and Tesseract integration.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter

from logging_service.logger import get_logger

logger = get_logger("capture.ocr_engine")


@dataclass
class OCRResult:
    """Outcome of an OCR extraction attempt."""
    text: str
    success: bool
    confidence: float = 0.0
    error_message: Optional[str] = None
    language: str = "eng"


class OCREngine:
    """
    Extracts text from screenshots using Tesseract with image preprocessing.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None, default_lang: str = "eng") -> None:
        self.default_lang = default_lang
        self.tesseract_cmd = tesseract_cmd or os.getenv("TESSERACT_CMD")
        self._is_available = False
        self._setup_tesseract()

    def _setup_tesseract(self) -> None:
        """Configures pytesseract executable location if present."""
        try:
            import pytesseract
            # Common paths on macOS and Linux
            candidates = [
                self.tesseract_cmd,
                shutil.which("tesseract"),
                "/opt/homebrew/bin/tesseract",
                "/usr/local/bin/tesseract",
                "/usr/bin/tesseract",
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            ]
            valid_path = next((p for p in candidates if p and os.path.exists(p)), None)
            if valid_path:
                pytesseract.pytesseract.tesseract_cmd = valid_path
                self._is_available = True
                logger.info("Tesseract OCR initialized at %s", valid_path)
            else:
                logger.info("Tesseract binary not found in standard paths. OCR fallback disabled.")
                self._is_available = False
        except ImportError:
            logger.info("pytesseract package not installed.")
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Enhances screenshot for OCR readability:
        - Grayscale conversion
        - Contrast enhancement
        - Median filtering to eliminate noise
        - Scaling up for high resolution
        """
        # Convert to grayscale
        gray = image.convert("L")

        # Scale up 2x using Lanczos if small
        if gray.width < 1200 or gray.height < 800:
            gray = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)

        # Light sharpening
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    def extract_text(
        self,
        image: Image.Image,
        lang: Optional[str] = None,
        preprocess: bool = True,
    ) -> OCRResult:
        """
        Runs OCR on given PIL Image with optional preprocessing.
        """
        if not self._is_available:
            return OCRResult(
                text="",
                success=False,
                error_message="Tesseract OCR binary is not installed or not in PATH.",
            )

        try:
            import pytesseract

            processed = self.preprocess_image(image) if preprocess else image
            target_lang = lang or self.default_lang

            # Page segmentation mode 6: Assume a single uniform block of text
            custom_config = r"--oem 3 --psm 6"
            text = pytesseract.image_to_string(processed, lang=target_lang, config=custom_config)

            raw_str = text if isinstance(text, str) else str(text or "")
            cleaned_text = raw_str.strip()
            return OCRResult(
                text=cleaned_text,
                success=bool(cleaned_text),
                language=target_lang,
            )
        except Exception as exc:
            logger.warning("OCR text extraction failed: %s", exc)
            return OCRResult(
                text="",
                success=False,
                error_message=str(exc),
            )

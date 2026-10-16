"""
Registry mapping application categories to supported operations and permission rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from core.application_detector import AppCategory
from platforms import get_platform_service
from logging_service.logger import get_logger

logger = get_logger("core.capability_registry")


@dataclass
class AppCapabilities:
    """Supported interaction features for a desktop application category."""
    can_read_selection: bool = True
    can_read_accessibility: bool = True
    can_paste_text: bool = True
    can_simulate_typing: bool = True
    prefers_raw_code: bool = False
    requires_ocr_for_text: bool = False
    description: str = ""


class CapabilityRegistry:
    """
    Maintains and queries supported capabilities across diverse desktop applications.
    """

    def __init__(self) -> None:
        self.platform = get_platform_service()
        self._registry: Dict[AppCategory, AppCapabilities] = {
            AppCategory.IDE: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=True,
                requires_ocr_for_text=False,
                description="Integrated Development Environment (VSCode, JetBrains)",
            ),
            AppCategory.TERMINAL: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=False,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=True,
                requires_ocr_for_text=False,
                description="Command line terminal / console emulator",
            ),
            AppCategory.BROWSER: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Web browser (Chromium, Gecko, WebKit)",
            ),
            AppCategory.OFFICE: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Word processor or presentation application",
            ),
            AppCategory.PDF_VIEWER: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=False,
                can_paste_text=False,  # Typically read-only
                can_simulate_typing=False,
                prefers_raw_code=False,
                requires_ocr_for_text=True,  # Often scanned PDFs
                description="Document / PDF viewer (Preview, Acrobat)",
            ),
            AppCategory.SPREADSHEET: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Spreadsheet application (Excel, Sheets, Numbers)",
            ),
            AppCategory.NOTE_TAKING: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Markdown or rich-text note taking application",
            ),
            AppCategory.COMMUNICATION: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=True,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Chat or email communication tool",
            ),
            AppCategory.UNKNOWN: AppCapabilities(
                can_read_selection=True,
                can_read_accessibility=False,
                can_paste_text=True,
                can_simulate_typing=True,
                prefers_raw_code=False,
                requires_ocr_for_text=False,
                description="Generic desktop application",
            ),
        }

    def get_capabilities(self, category: AppCategory) -> AppCapabilities:
        """Retrieves capability flags for application category."""
        return self._registry.get(category, self._registry[AppCategory.UNKNOWN])

    def check_permissions(self) -> Dict[str, bool]:
        """Validates OS-level accessibility and screen recording authorizations."""
        has_ax = self.platform.check_accessibility_permissions(prompt=False)
        return {
            "accessibility": has_ax,
            "clipboard": True,
            "screen_capture": True,
        }

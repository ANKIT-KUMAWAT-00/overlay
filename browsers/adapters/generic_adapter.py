"""
Generic reusable desktop browser adapter.
"""

from __future__ import annotations

import time
from typing import Optional, List, Dict, Any

from browsers.base_adapter import BrowserAdapter, BrowserCapabilities
from browsers.capability_detection import BrowserCapabilityDetector
from platforms import get_platform_service
from capture.screen_capture import ScreenCaptureService
from delivery.clipboard_service import ClipboardService
from logging_service.logger import get_logger

logger = get_logger("browsers.adapters.generic")


class GenericBrowserAdapter(BrowserAdapter):
    """
    Standard browser adapter utilizing platform selection hooks, clipboard, and screen capture.
    """

    def __init__(self, browser_name: str = "Browser", app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(browser_name, app_info)
        self.platform = get_platform_service()
        self.screen_capture = ScreenCaptureService()
        self.clipboard = ClipboardService()
        self._capabilities = BrowserCapabilityDetector.evaluate(self.browser_name, self.app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        title = curr.get("window_title", "").lower()
        target = self.browser_name.lower()
        return target in name or target in title

    def get_capabilities(self) -> BrowserCapabilities:
        return self._capabilities

    def get_selected_text(self) -> Optional[str]:
        if not self._capabilities.can_get_selected_text:
            return None
        return self.platform.get_selected_text_via_clipboard()

    def get_visible_text(self) -> Optional[str]:
        if not self._capabilities.can_get_visible_text:
            return None
        # Fall back to empty or accessibility inspection
        return None

    def capture_visible_region(self) -> Optional[bytes]:
        if not self._capabilities.can_capture_visible_region:
            return None
        try:
            img = self.screen_capture.capture_fullscreen()
            return self.screen_capture.image_to_bytes(img, format="JPEG", quality=80)
        except Exception as exc:
            logger.warning("Browser viewport capture error: %s", exc)
            return None

    def identify_editable_targets(self) -> List[str]:
        if not self._capabilities.can_identify_editable_targets:
            return []
        return ["WebArea:ActiveInput"]

    def insert_text(self, text: str) -> bool:
        if not self._capabilities.can_insert_text or not text:
            return False
        return self.platform.insert_text(text, method="clipboard")

    def copy_text(self, text: str) -> bool:
        return self.clipboard.copy(text)

    def verify_result(self) -> bool:
        return self.detect_browser()

    def dispose(self) -> None:
        logger.debug("Disposed browser adapter for %s", self.browser_name)

"""
Text insertion into active applications with focus verification and multiple methods.
"""

from __future__ import annotations

import platform
import time
from enum import Enum
from typing import Optional

from platforms import get_platform_service
from delivery.clipboard_service import ClipboardService
from logging_service.logger import get_logger

logger = get_logger("delivery.text_insertion")


class InsertionMethod(str, Enum):
    """Supported text injection techniques."""
    CLIPBOARD_PASTE = "clipboard_paste"
    SIMULATED_TYPING = "simulated_typing"
    ACCESSIBILITY = "accessibility"


class TextInsertionService:
    """
    Safely injects text into the frontmost application.
    Enforces target window verification to prevent unintended text delivery.
    """

    def __init__(self, clipboard: Optional[ClipboardService] = None) -> None:
        self.clipboard = clipboard or ClipboardService()
        self.platform = get_platform_service()
        self.os_type = platform.system()

    def verify_target_focus(
        self,
        expected_app_name: Optional[str] = None,
        expected_window_title: Optional[str] = None,
        force_insert: bool = False,
    ) -> bool:
        """
        Verifies that the expected application or window is in focus.
        """
        # Never deliver into OmniAssist itself
        if expected_app_name and "omniassist" in expected_app_name.lower():
            return False

        # Allow brief window manager focus transition
        curr_app = ""
        curr_title = ""
        for _ in range(5):
            curr_info = self.platform.get_active_app_info()
            curr_app = curr_info.get("app_name", "")
            curr_title = curr_info.get("window_title", "")
            if any(k in curr_app.lower() or k in curr_title.lower() for k in ("omniassist",)):
                time.sleep(0.06)
                continue
            break

        # Abort if front window is still OmniAssist
        if any(k in curr_app.lower() or k in curr_title.lower() for k in ("omniassist",)):
            logger.warning("Target window is OmniAssist itself. Aborting insertion to avoid loop.")
            return False

        # When user pressed Option+Enter / Force Insert, insert directly into frontmost app
        if force_insert:
            logger.info("Force insertion enabled; delivering to active target app: '%s'", curr_app)
            return True

        if not expected_app_name and not expected_window_title:
            return True

        # Fuzzy match for expected app name
        if expected_app_name and expected_app_name.lower() not in ("unknown", "active application"):
            exp = expected_app_name.lower()
            cur = curr_app.lower()
            if exp not in cur and cur not in exp:
                logger.warning(
                    "Target application mismatch: expected '%s', found '%s'",
                    expected_app_name,
                    curr_app,
                )
                return False

        return True

    def insert(
        self,
        text: str,
        method: InsertionMethod = InsertionMethod.CLIPBOARD_PASTE,
        expected_app: Optional[str] = None,
        expected_title: Optional[str] = None,
        typing_delay_ms: int = 10,
        force_insert: bool = False,
    ) -> bool:
        """
        Executes verified text injection.
        """
        if not text:
            return False

        # Target focus check
        if not self.verify_target_focus(expected_app, expected_title, force_insert=force_insert):
            logger.error("Target window focus verification failed. Aborting insertion.")
            return False

        if method == InsertionMethod.CLIPBOARD_PASTE:
            return self._insert_via_clipboard(text)
        elif method == InsertionMethod.SIMULATED_TYPING:
            return self._insert_via_typing(text, typing_delay_ms)
        elif method == InsertionMethod.ACCESSIBILITY:
            return self._insert_via_accessibility(text)

        return False

    def _insert_via_clipboard(self, text: str) -> bool:
        """Copies text and triggers OS paste hotkey."""
        success = self.clipboard.copy(text)
        if not success:
            return False

        time.sleep(0.06)  # Give OS clipboard buffer time to register
        return self.platform.insert_text(text, method="clipboard")

    def _insert_via_typing(self, text: str, delay_ms: int) -> bool:
        """Types characters sequentially via pyautogui."""
        try:
            import pyautogui
            delay_sec = max(0.001, delay_ms / 1000.0)
            pyautogui.write(text, interval=delay_sec)
            return True
        except Exception as exc:
            logger.error("Simulated typing injection failed: %s", exc)
            return False

    def _insert_via_accessibility(self, text: str) -> bool:
        """Directly writes value to focused accessibility control if supported."""
        # Fall back to clipboard paste if direct AX value writing is not available
        return self._insert_via_clipboard(text)

"""
Windows-specific OS integration, Win32 API window queries, and keyboard simulation.
"""

from __future__ import annotations

import ctypes
import platform
import time
from typing import Optional, Dict, Any

from logging_service.logger import get_logger

logger = get_logger("platforms.windows")


class WindowsPlatform:
    """Windows platform integration using ctypes and Win32 APIs."""

    def __init__(self) -> None:
        self.is_windows = platform.system() == "Windows"

    def check_accessibility_permissions(self, prompt: bool = False) -> bool:
        """On Windows, standard desktop apps have access by default unless blocked by UAC/UIPI."""
        return True

    def get_active_app_info(self) -> Dict[str, Any]:
        """
        Retrieves active foreground window title, process ID, and application name.
        """
        info: Dict[str, Any] = {
            "app_name": "Unknown",
            "bundle_id": "",
            "window_title": "",
            "pid": 0,
        }

        if not self.is_windows:
            return info

        try:
            windll = getattr(ctypes, "windll", None)
            if not windll:
                return info
            user32 = windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return info

            # Window Title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            info["window_title"] = buff.value

            # Process ID
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            info["pid"] = pid.value

            # Process Name via psutil or Kernel32 if available
            try:
                import psutil
                proc = psutil.Process(pid.value)
                info["app_name"] = proc.name()
                info["bundle_id"] = proc.exe()
            except Exception:
                info["app_name"] = info["window_title"] or "WindowsApp"

        except Exception as exc:
            logger.debug("Win32 active window lookup failed: %s", exc)

        return info

    def get_selected_text_via_clipboard(self, restore_clipboard: bool = True) -> Optional[str]:
        """
        Simulates Ctrl+C with clipboard preservation to safely capture selection.
        """
        import pyperclip

        old_clip = None
        if restore_clipboard:
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = None

        sentinel = f"__omni_sentinel_{int(time.time() * 1000)}__"
        try:
            pyperclip.copy(sentinel)
        except Exception:
            pass

        # Simulate Ctrl+C via pyautogui
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.08)
        except Exception as exc:
            logger.warning("Windows Ctrl+C simulation failed: %s", exc)

        try:
            new_clip = pyperclip.paste()
            selected = None
            if new_clip and new_clip != sentinel:
                selected = new_clip

            if restore_clipboard and old_clip is not None:
                pyperclip.copy(old_clip)

            return selected
        except Exception as exc:
            logger.warning("Windows clipboard read failed: %s", exc)
            return None

    def insert_text(self, text: str, method: str = "clipboard") -> bool:
        """
        Inserts text into the active Windows application via Ctrl+V.
        """
        if not text:
            return False

        if method == "clipboard":
            import pyperclip
            try:
                pyperclip.copy(text)
                time.sleep(0.05)
                import pyautogui
                pyautogui.hotkey("ctrl", "v")
                return True
            except Exception as exc:
                logger.error("Windows paste insertion failed: %s", exc)
                return False

        return False

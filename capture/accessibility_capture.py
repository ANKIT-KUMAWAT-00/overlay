"""
Accessibility-based text extraction from focused native application controls.
"""

from __future__ import annotations

import platform
import subprocess
from typing import Optional, Tuple

from logging_service.logger import get_logger

logger = get_logger("capture.accessibility_capture")


class AccessibilityCaptureService:
    """
    Extracts text and values from GUI accessibility trees.
    """

    def __init__(self) -> None:
        self.os_type = platform.system()

    def capture_focused_text(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempts to read the currently focused text field or selection via OS accessibility.
        Returns (text, control_type).
        """
        if self.os_type == "Darwin":
            return self._capture_macos_focused()
        elif self.os_type == "Windows":
            return self._capture_windows_focused()
        return None, None

    def _capture_macos_focused(self) -> Tuple[Optional[str], Optional[str]]:
        """Queries focused UI element value via AppleScript System Events."""
        script = """
        tell application "System Events"
            set frontProc to first application process whose frontmost is true
            tell frontProc
                try
                    set focusedElem to focused of front window
                    set elemVal to value of focusedElem
                    set elemRole to role of focusedElem
                    return elemRole & "|||" & (elemVal as text)
                on error
                    try
                        -- Try getting selected text from entire window
                        set selText to value of attribute "AXSelectedText" of front window
                        return "AXSelectedText|||" & (selText as text)
                    on error
                        return ""
                    end try
                end try
            end tell
        end tell
        """
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("|||", 1)
                role = parts[0] if len(parts) > 0 else "AXUnknown"
                val = parts[1] if len(parts) > 1 else ""
                if val:
                    return val.strip(), role
        except Exception as exc:
            logger.debug("macOS accessibility extraction failed: %s", exc)

        return None, None

    def _capture_windows_focused(self) -> Tuple[Optional[str], Optional[str]]:
        """Windows UI Automation text extraction fallback."""
        # Windows UI Automation via comtypes or pywin32 if available
        try:
            import uiautomation as uia  # type: ignore
            focused = uia.GetFocusedControl()
            if focused:
                val = focused.GetValuePattern().Value if hasattr(focused, "GetValuePattern") else focused.Name
                return val, focused.ControlTypeName
        except Exception:
            pass
        return None, None

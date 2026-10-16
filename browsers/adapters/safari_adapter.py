"""
Apple Safari browser adapter.
"""

from __future__ import annotations

import subprocess
from typing import Optional, Dict, Any
from browsers.adapters.generic_adapter import GenericBrowserAdapter
from logging_service.logger import get_logger

logger = get_logger("browsers.adapters.safari")


class SafariBrowserAdapter(GenericBrowserAdapter):
    """Adapter for Apple Safari on macOS."""

    def __init__(self, app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Safari", app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        bundle = curr.get("bundle_id", "").lower()
        return "safari" in name or "com.apple.safari" in bundle

    def get_visible_text(self) -> Optional[str]:
        """Queries active Safari tab text via AppleScript if permitted."""
        script = """
        tell application "Safari"
            try
                return text of current tab of front window
            on error
                return ""
            end try
        end tell
        """
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as exc:
            logger.debug("Safari AppleScript text extraction failed: %s", exc)
        return None

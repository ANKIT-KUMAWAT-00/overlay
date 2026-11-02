"""
Platform abstraction layer for Windows and macOS.
"""

from __future__ import annotations

import platform
from .macos import MacOSPlatform
from .windows import WindowsPlatform

__all__ = [
    "get_platform_service",
    "exclude_window_from_screen_capture",
    "MacOSPlatform",
    "WindowsPlatform",
]


def get_platform_service():
    """Returns the OS-specific platform implementation."""
    os_name = platform.system()
    if os_name == "Darwin":
        return MacOSPlatform()
    elif os_name == "Windows":
        return WindowsPlatform()
    else:
        # Fallback to generic macOS/Linux compatible behavior
        return MacOSPlatform()


def exclude_window_from_screen_capture(qwidget) -> bool:
    """Helper to exclude a PySide6 QWidget from OS screen captures."""
    try:
        service = get_platform_service()
        if hasattr(service, "exclude_window_from_screen_capture"):
            return service.exclude_window_from_screen_capture(qwidget)
    except Exception:
        pass
    return False

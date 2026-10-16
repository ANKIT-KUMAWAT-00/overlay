"""
Platform abstraction layer for Windows and macOS.
"""

from __future__ import annotations

import platform
from .macos import MacOSPlatform
from .windows import WindowsPlatform

__all__ = ["get_platform_service", "MacOSPlatform", "WindowsPlatform"]


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

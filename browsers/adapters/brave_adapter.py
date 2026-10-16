"""
Brave Browser adapter with shields awareness.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from browsers.adapters.generic_adapter import GenericBrowserAdapter


class BraveBrowserAdapter(GenericBrowserAdapter):
    """Adapter for Brave Browser."""

    def __init__(self, app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Brave Browser", app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        bundle = curr.get("bundle_id", "").lower()
        return "brave" in name or "com.brave.browser" in bundle

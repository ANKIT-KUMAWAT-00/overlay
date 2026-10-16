"""
Google Chrome browser adapter.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from browsers.adapters.generic_adapter import GenericBrowserAdapter


class ChromeBrowserAdapter(GenericBrowserAdapter):
    """Adapter for Google Chrome."""

    def __init__(self, app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Google Chrome", app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        bundle = curr.get("bundle_id", "").lower()
        return "chrome" in name or "com.google.chrome" in bundle

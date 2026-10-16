"""
Microsoft Edge browser adapter.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from browsers.adapters.generic_adapter import GenericBrowserAdapter


class EdgeBrowserAdapter(GenericBrowserAdapter):
    """Adapter for Microsoft Edge."""

    def __init__(self, app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Microsoft Edge", app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        bundle = curr.get("bundle_id", "").lower()
        return "edge" in name or "com.microsoft.edgemac" in bundle

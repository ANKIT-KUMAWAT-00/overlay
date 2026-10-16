"""
Tor Browser adapter with strict isolation and privacy protections.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from browsers.adapters.generic_adapter import GenericBrowserAdapter
from logging_service.logger import get_logger

logger = get_logger("browsers.adapters.tor")


class TorBrowserAdapter(GenericBrowserAdapter):
    """
    Tor Browser adapter.
    Respects strict anti-fingerprinting; disables any DOM or automation attempts.
    Relies safely on user-initiated selection and screen capture.
    """

    def __init__(self, app_info: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Tor Browser", app_info)

    def detect_browser(self) -> bool:
        curr = self.platform.get_active_app_info()
        name = curr.get("app_name", "").lower()
        title = curr.get("window_title", "").lower()
        bundle = curr.get("bundle_id", "").lower()
        return "tor browser" in name or "tor" in bundle or "tor browser" in title

    def identify_editable_targets(self) -> List[str]:
        # Tor blocks DOM accessibility hooks for fingerprinting resistance
        return []

    def get_visible_text(self) -> Optional[str]:
        # Never inject scripts or query DOM in Tor
        return None

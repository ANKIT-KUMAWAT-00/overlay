"""
Browser detection and adapter registry dispatcher.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Type, Callable

from browsers.base_adapter import BrowserAdapter
from browsers.adapters.chrome_adapter import ChromeBrowserAdapter
from browsers.adapters.safari_adapter import SafariBrowserAdapter
from browsers.adapters.firefox_adapter import FirefoxBrowserAdapter
from browsers.adapters.brave_adapter import BraveBrowserAdapter
from browsers.adapters.edge_adapter import EdgeBrowserAdapter
from browsers.adapters.tor_adapter import TorBrowserAdapter
from browsers.adapters.librewolf_adapter import LibreWolfBrowserAdapter
from browsers.adapters.generic_adapter import GenericBrowserAdapter
from platforms import get_platform_service
from logging_service.logger import get_logger

logger = get_logger("browsers.browser_detection")


class BrowserDetector:
    """
    Identifies the active browser from application metadata and instantiates its adapter.
    """

    ADAPTER_CLASSES: List[Callable[[Optional[Dict[str, Any]]], BrowserAdapter]] = [
        BraveBrowserAdapter,
        TorBrowserAdapter,
        LibreWolfBrowserAdapter,
        ChromeBrowserAdapter,
        EdgeBrowserAdapter,
        SafariBrowserAdapter,
        FirefoxBrowserAdapter,
    ]

    def __init__(self) -> None:
        self.platform = get_platform_service()

    def get_active_browser_adapter(self) -> Optional[BrowserAdapter]:
        """
        Detects if the foreground application is a supported browser and returns its adapter.
        """
        app_info = self.platform.get_active_app_info()
        app_name = app_info.get("app_name", "").lower()
        bundle_id = app_info.get("bundle_id", "").lower()

        logger.debug("Inspecting foreground app for browser match: %s (%s)", app_name, bundle_id)

        for adapter_cls in self.ADAPTER_CLASSES:
            instance = adapter_cls(app_info)
            if instance.detect_browser():
                logger.info("Matched active browser adapter: %s", instance.browser_name)
                return instance

        # Fallback check for generic browser terms
        if any(term in app_name for term in ("browser", "web", "navigator")):
            logger.info("Matched generic browser fallback for '%s'", app_name)
            return GenericBrowserAdapter(browser_name=app_name, app_info=app_info)

        return None

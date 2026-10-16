"""
Browser capability inspection and sandbox/privacy analysis.
"""

from __future__ import annotations

import platform
from typing import Dict, Any

from browsers.base_adapter import BrowserCapabilities
from logging_service.logger import get_logger

logger = get_logger("browsers.capability_detection")


class BrowserCapabilityDetector:
    """
    Evaluates individual browser capabilities without assuming uniform interface support.
    """

    @staticmethod
    def evaluate(browser_name: str, app_info: Dict[str, Any]) -> BrowserCapabilities:
        b_name = browser_name.lower()
        os_type = platform.system()

        # Tor Browser: Extreme privacy hardening, no automation, no external DOM probing
        if "tor" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=False,
                can_capture_visible_region=True,
                can_identify_editable_targets=False,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=True,
                isolation_notes="Tor anti-fingerprinting and strict isolation active. OCR and selection supported.",
            )

        # LibreWolf: Firefox fork with RFP (Resist Fingerprinting)
        if "librewolf" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=False,
                can_capture_visible_region=True,
                can_identify_editable_targets=False,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=True,
                isolation_notes="LibreWolf privacy protections active. Standard selection & paste injection supported.",
            )

        # Brave: Shields active, Chromium-based
        if "brave" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=True,
                can_capture_visible_region=True,
                can_identify_editable_targets=True,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=True,
                isolation_notes="Brave Shields enabled. Chromium accessibility API accessible.",
            )

        # DuckDuckGo Browser
        if "duckduckgo" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=False,
                can_capture_visible_region=True,
                can_identify_editable_targets=False,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=True,
                isolation_notes="DuckDuckGo privacy protections active.",
            )

        # Safari: macOS native, AppleScript supported if enabled
        if "safari" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=True,
                can_capture_visible_region=True,
                can_identify_editable_targets=True,
                can_insert_text=True,
                supports_automation_api=os_type == "Darwin",
                privacy_hardened=False,
                isolation_notes="macOS native Safari AX and AppleScript hooks supported.",
            )

        # Chrome & Edge: Chromium accessibility
        if "chrome" in b_name or "edge" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=True,
                can_capture_visible_region=True,
                can_identify_editable_targets=True,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=False,
                isolation_notes="Full Chromium accessibility and paste injection supported.",
            )

        # Firefox
        if "firefox" in b_name:
            return BrowserCapabilities(
                can_get_selected_text=True,
                can_get_visible_text=False,
                can_capture_visible_region=True,
                can_identify_editable_targets=True,
                can_insert_text=True,
                supports_automation_api=False,
                privacy_hardened=False,
                isolation_notes="Gecko engine accessibility supported.",
            )

        # Default fallback
        return BrowserCapabilities(
            can_get_selected_text=True,
            can_get_visible_text=False,
            can_capture_visible_region=True,
            can_identify_editable_targets=False,
            can_insert_text=True,
            supports_automation_api=False,
            privacy_hardened=False,
            isolation_notes="Generic desktop browser fallback.",
        )

"""
Abstract base adapter interface and capability models for web browsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from logging_service.logger import get_logger

logger = get_logger("browsers.base_adapter")


@dataclass
class BrowserCapabilities:
    """Individual capability flags supported by a specific browser adapter."""
    can_get_selected_text: bool = True
    can_get_visible_text: bool = False
    can_capture_visible_region: bool = True
    can_identify_editable_targets: bool = False
    can_insert_text: bool = True
    supports_automation_api: bool = False
    privacy_hardened: bool = False
    isolation_notes: str = ""


class BrowserAdapter(ABC):
    """
    Standard interface for browser detection, text capture, and insertion.
    Respects strict privacy sandboxing and platform accessibility boundaries.
    """

    def __init__(self, browser_name: str = "Browser", app_info: Optional[Dict[str, Any]] = None) -> None:
        self.browser_name = browser_name
        self.app_info = app_info or {}

    @abstractmethod
    def detect_browser(self) -> bool:
        """Determines if the current active process/window matches this browser."""
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> BrowserCapabilities:
        """Reports concrete capabilities for this browser environment."""
        raise NotImplementedError

    @abstractmethod
    def get_selected_text(self) -> Optional[str]:
        """Reads highlighted or selected text from the browser view."""
        raise NotImplementedError

    @abstractmethod
    def get_visible_text(self) -> Optional[str]:
        """Reads visible text from active tab or accessibility tree."""
        raise NotImplementedError

    @abstractmethod
    def capture_visible_region(self) -> Optional[bytes]:
        """Captures a screenshot of the browser viewport."""
        raise NotImplementedError

    @abstractmethod
    def identify_editable_targets(self) -> List[str]:
        """Identifies whether an active text input or contenteditable element has focus."""
        raise NotImplementedError

    @abstractmethod
    def insert_text(self, text: str) -> bool:
        """Inserts text into the active focused input field in the browser."""
        raise NotImplementedError

    @abstractmethod
    def copy_text(self, text: str) -> bool:
        """Copies text safely into system clipboard."""
        raise NotImplementedError

    @abstractmethod
    def verify_result(self) -> bool:
        """Verifies that the target browser window remains active and responsive."""
        raise NotImplementedError

    @abstractmethod
    def dispose(self) -> None:
        """Cleans up any allocated resources or connections."""
        raise NotImplementedError

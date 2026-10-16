"""
Universal active application detection and classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from platforms import get_platform_service
from logging_service.logger import get_logger

logger = get_logger("core.application_detector")


class AppCategory(str, Enum):
    """Categorization of desktop software."""
    BROWSER = "browser"
    IDE = "ide"
    TEXT_EDITOR = "text_editor"
    OFFICE = "office"
    PDF_VIEWER = "pdf_viewer"
    SPREADSHEET = "spreadsheet"
    NOTE_TAKING = "note_taking"
    COMMUNICATION = "communication"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


@dataclass
class DetectedApplication:
    """Rich metadata about the active foreground application."""
    name: str
    category: AppCategory
    bundle_id: str = ""
    window_title: str = ""
    pid: int = 0
    is_browser: bool = False
    is_code_editor: bool = False


class ApplicationDetector:
    """
    Introspects OS foreground process and classifies into functional categories.
    """

    IDE_SIGNATURES = [
        "code", "visual studio", "cursor", "pycharm", "intellij", "webstorm",
        "clion", "rubymine", "sublime", "xcode", "eclipse", "atom", "zed",
    ]
    TERMINAL_SIGNATURES = [
        "terminal", "iterm", "alacritty", "kitty", "warp", "hyper", "powershell", "cmd", "wezterm",
    ]
    BROWSER_SIGNATURES = [
        "chrome", "safari", "firefox", "brave", "edge", "opera", "vivaldi", "tor", "librewolf", "arc",
    ]
    OFFICE_SIGNATURES = [
        "word", "pages", "writer", "libreoffice", "microsoft word",
    ]
    SPREADSHEET_SIGNATURES = [
        "excel", "numbers", "calc", "google sheets",
    ]
    NOTE_SIGNATURES = [
        "notes", "obsidian", "notion", "bear", "onenote", "evernote", "logseq",
    ]
    PDF_SIGNATURES = [
        "acrobat", "preview", "reader", "pdf", "skim",
    ]
    COMM_SIGNATURES = [
        "slack", "teams", "discord", "telegram", "whatsapp", "signal", "mail", "outlook",
    ]

    def __init__(self) -> None:
        self.platform = get_platform_service()

    def detect_active_application(self) -> DetectedApplication:
        """
        Determines current active application and its classification category.
        """
        app_info = self.platform.get_active_app_info()
        name = app_info.get("app_name", "Unknown")
        bundle = app_info.get("bundle_id", "")
        title = app_info.get("window_title", "")
        pid = app_info.get("pid", 0)

        search_str = f"{name} {bundle} {title}".lower()

        category = AppCategory.UNKNOWN
        is_browser = False
        is_code_editor = False

        if any(sig in search_str for sig in self.BROWSER_SIGNATURES):
            category = AppCategory.BROWSER
            is_browser = True
        elif any(sig in search_str for sig in self.IDE_SIGNATURES):
            category = AppCategory.IDE
            is_code_editor = True
        elif any(sig in search_str for sig in self.TERMINAL_SIGNATURES):
            category = AppCategory.TERMINAL
            is_code_editor = True
        elif any(sig in search_str for sig in self.SPREADSHEET_SIGNATURES):
            category = AppCategory.SPREADSHEET
        elif any(sig in search_str for sig in self.OFFICE_SIGNATURES):
            category = AppCategory.OFFICE
        elif any(sig in search_str for sig in self.NOTE_SIGNATURES):
            category = AppCategory.NOTE_TAKING
        elif any(sig in search_str for sig in self.PDF_SIGNATURES):
            category = AppCategory.PDF_VIEWER
        elif any(sig in search_str for sig in self.COMM_SIGNATURES):
            category = AppCategory.COMMUNICATION

        logger.debug(
            "Detected active application: '%s' (category=%s, window='%s')",
            name,
            category.value,
            title,
        )

        return DetectedApplication(
            name=name,
            category=category,
            bundle_id=bundle,
            window_title=title,
            pid=pid,
            is_browser=is_browser,
            is_code_editor=is_code_editor,
        )

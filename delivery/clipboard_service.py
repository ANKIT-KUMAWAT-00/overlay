"""
Cross-platform clipboard management service using pyperclip with error handling.
"""

from __future__ import annotations

import time
from typing import Optional

from logging_service.logger import get_logger

logger = get_logger("delivery.clipboard")


class ClipboardService:
    """
    Manages safe reading, writing, and backup/restore of system clipboard.
    """

    def __init__(self) -> None:
        pass

    def copy(self, text: str) -> bool:
        """Copies text to the system clipboard."""
        if text is None:
            return False
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info("Copied %d characters to clipboard", len(text))
            return True
        except Exception as exc:
            logger.error("Failed to copy to clipboard: %s", exc)
            return False

    def paste(self) -> Optional[str]:
        """Reads current content from clipboard."""
        try:
            import pyperclip
            content = pyperclip.paste()
            return content
        except Exception as exc:
            logger.error("Failed to read from clipboard: %s", exc)
            return None

    def clear(self) -> bool:
        """Clears clipboard content."""
        return self.copy("")

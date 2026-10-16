"""
Answer delivery coordinator managing clipboard copying, insertion, and telemetry.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from delivery.clipboard_service import ClipboardService
from delivery.text_insertion import TextInsertionService, InsertionMethod
from config.settings import AppSettings, get_settings
from logging_service.logger import get_logger

logger = get_logger("delivery.answer_delivery")


@dataclass
class DeliveryResult:
    """Outcome of an answer delivery action."""
    success: bool
    copied_to_clipboard: bool = False
    inserted_to_app: bool = False
    method_used: str = "none"
    target_app: str = "Unknown"
    error_message: Optional[str] = None


class AnswerDeliveryCoordinator:
    """
    Coordinates delivery of the finalized answer into the user's workspace.
    """

    def __init__(
        self,
        clipboard: Optional[ClipboardService] = None,
        insertion: Optional[TextInsertionService] = None,
        settings: Optional[AppSettings] = None,
    ) -> None:
        self.clipboard = clipboard or ClipboardService()
        self.insertion = insertion or TextInsertionService(self.clipboard)
        self.settings = settings or get_settings()

    def deliver(
        self,
        answer_text: str,
        target_app: Optional[str] = None,
        target_title: Optional[str] = None,
        force_insert: bool = False,
        force_copy: bool = False,
    ) -> DeliveryResult:
        """
        Executes delivery based on preferences and caller flags.
        """
        if not answer_text:
            return DeliveryResult(
                success=False,
                error_message="Answer text is empty; nothing to deliver.",
            )

        delivery_cfg = self.settings.delivery
        should_copy = force_copy or delivery_cfg.auto_copy_to_clipboard
        should_insert = force_insert or delivery_cfg.auto_insert_to_active_app

        copied = False
        inserted = False
        error_msg = None
        method_used = "none"

        # 1. Clipboard Copy
        if should_copy:
            copied = self.clipboard.copy(answer_text)
            if copied:
                method_used = "clipboard_copy"
            else:
                error_msg = "Failed to copy answer to clipboard."

        # 2. Direct Application Insertion
        if should_insert:
            logger.info("Attempting direct insertion into target app '%s'...", target_app)
            time.sleep(0.1)  # Allow active window focus to settle if switching from HUD

            inserted = self.insertion.insert(
                text=answer_text,
                method=InsertionMethod.CLIPBOARD_PASTE,
                expected_app=target_app,
                expected_title=target_title,
                typing_delay_ms=delivery_cfg.simulate_typing_delay_ms,
                force_insert=force_insert,
            )
            if inserted:
                method_used = "direct_insertion"
            else:
                msg = f"Direct insertion failed into target app '{target_app}'."
                error_msg = f"{error_msg} | {msg}" if error_msg else msg
                logger.warning(msg)

        is_success = copied or inserted
        return DeliveryResult(
            success=is_success,
            copied_to_clipboard=copied,
            inserted_to_app=inserted,
            method_used=method_used,
            target_app=target_app or "Unknown",
            error_message=error_msg,
        )

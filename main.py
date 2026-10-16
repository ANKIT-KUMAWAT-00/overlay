"""
Main entry point for OmniAssist Python Desktop Assistant.
"""

from __future__ import annotations

import argparse
import os
import sys

from logging_service.logger import configure_logging, get_logger
from config.settings import get_settings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OmniAssist - Universal AI Desktop Assistant",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable system tray icon",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless terminal background mode without Qt GUI",
    )
    return parser.parse_args()


def run_gui_application(args: argparse.Namespace) -> int:
    """Launches the PySide6 desktop GUI and tray application."""
    from PySide6.QtWidgets import QApplication
    from app.application import OmniAssistantApplication

    # High-DPI and platform attributes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("OmniAssist")
    app.setApplicationDisplayName("OmniAssist AI")
    app.setOrganizationName("OmniAssist")
    app.setOrganizationDomain("omniassist.ai")

    settings = get_settings()
    if args.no_tray:
        settings.ui.show_tray_icon = False

    assistant_app = OmniAssistantApplication(app, settings=settings)
    assistant_app.start()

    # Graceful Ctrl+C shutdown handler in terminal
    import signal
    from PySide6.QtCore import QTimer
    signal.signal(signal.SIGINT, lambda *_: assistant_app.quit_application())
    sig_timer = QTimer()
    sig_timer.start(300)
    sig_timer.timeout.connect(lambda: None)

    logger = get_logger("main")
    logger.info("OmniAssist GUI running. Press global shortcut to activate.")

    return app.exec()


def run_headless_application(args: argparse.Namespace) -> int:
    """Launches lightweight CLI background daemon."""
    import time
    from app.lifecycle import LifecycleManager
    from core.orchestrator import AssistantOrchestrator

    logger = get_logger("main.headless")
    logger.info("Starting OmniAssist in headless background mode...")

    orchestrator = AssistantOrchestrator()
    lifecycle = LifecycleManager()

    def _trigger_interaction() -> None:
        orchestrator.run_interaction_async()

    lifecycle.shortcuts.on_activate = _trigger_interaction
    lifecycle.startup()

    logger.info("Headless daemon active. Global shortcuts listening. Press Ctrl+C to terminate.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Shutting down headless assistant...")
    finally:
        lifecycle.shutdown()

    return 0


def main() -> int:
    args = parse_arguments()

    import logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_logging(level=log_level)

    logger = get_logger("main")
    logger.info("Initializing OmniAssist Python Desktop Assistant...")

    # Determine if GUI is available or requested
    has_display = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY") or sys.platform in ("darwin", "win32"))
    if args.headless or not has_display:
        return run_headless_application(args)

    try:
        return run_gui_application(args)
    except Exception as exc:
        logger.critical("Fatal error starting OmniAssist: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

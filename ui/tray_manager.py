"""
System tray icon and macOS menu-bar management using PySide6.
"""

from __future__ import annotations

from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from logging_service.logger import get_logger

logger = get_logger("ui.tray_manager")


class TrayManager(QObject):
    """
    Manages system tray icon, notifications, and menu bar actions.
    """

    activate_requested = Signal()
    capture_region_requested = Signal()
    open_hud_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self._init_icon()
        self._init_menu()

    def _init_icon(self) -> None:
        """Generates a crisp geometric icon pixmap for menu bar and tray."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gradient circle
        painter.setBrush(QColor(99, 102, 241))  # Indigo
        painter.setPen(QColor(129, 140, 248))  # Light indigo border
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

        # Inner spark symbol
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), 0x0084, "Ω")  # AlignCenter
        painter.end()

        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("OmniAssist - Universal AI Desktop Assistant")

    def _init_menu(self) -> None:
        """Constructs context menu for tray icon."""
        menu = QMenu()

        action_activate = menu.addAction("⚡ Activate OmniAssist")
        action_activate.triggered.connect(self.activate_requested.emit)

        action_capture = menu.addAction("✂ Capture Screen Region")
        action_capture.triggered.connect(self.capture_region_requested.emit)

        action_hud = menu.addAction("🖥 Open Assistant HUD")
        action_hud.triggered.connect(self.open_hud_requested.emit)

        menu.addSeparator()

        action_settings = menu.addAction("⚙ Settings...")
        action_settings.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        action_quit = menu.addAction("✕ Quit OmniAssist")
        action_quit.triggered.connect(self.quit_requested.emit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Single or double click brings up HUD."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_hud_requested.emit()

    def show(self) -> None:
        """Displays tray icon in system notification area."""
        self.tray_icon.show()
        logger.info("System tray icon displayed.")

    def hide(self) -> None:
        self.tray_icon.hide()

    def show_message(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information) -> None:
        """Displays OS desktop notification."""
        self.tray_icon.showMessage(title, message, icon, 3000)

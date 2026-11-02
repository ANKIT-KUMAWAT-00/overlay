"""
Interactive screen region snipping overlay.
Allows user to select a rectangular screen region while keeping all assistant
windows hidden from the captured screenshot.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QKeyEvent
from PySide6.QtWidgets import QWidget, QApplication

from capture.screen_capture import ScreenRegion
from platforms import exclude_window_from_screen_capture
from logging_service.logger import get_logger

logger = get_logger("ui.snipping_overlay")


class SnippingOverlay(QWidget):
    """
    Fullscreen translucent overlay allowing the user to click and drag to select
    a screen region. Automatically hides itself before region capture.
    """

    region_selected = Signal(object)  # ScreenRegion
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting: bool = False

    def start_selection(self) -> None:
        """Presents fullscreen snipping overlay across all connected monitors."""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.virtualGeometry()
                self.setGeometry(geo)
        except Exception as exc:
            logger.warning("Error querying virtual geometry: %s", exc)

        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        exclude_window_from_screen_capture(self)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # 1. Dark semi-transparent scrim over screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._start_pos and self._current_pos:
            rect = QRect(self._start_pos, self._current_pos).normalized()

            # 2. Punch transparent hole through scrim for the selected region
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)

            # 3. Draw high-visibility border around selected area
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(99, 102, 241), 2)  # Modern Indigo accent
            painter.setPen(pen)
            painter.drawRect(rect)

            # 4. Dimension badge
            dim_text = f" {rect.width()} × {rect.height()} px "
            painter.setFont(QFont("-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", 10, QFont.Weight.Bold))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(17, 24, 39, 220))
            text_rect = QRect(rect.left(), max(0, rect.top() - 24), 110, 20)
            painter.drawRoundedRect(text_rect, 4, 4)
            painter.setPen(QColor(243, 244, 246))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, dim_text)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.globalPosition().toPoint()
            self._current_pos = self._start_pos
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._is_selecting:
            self._current_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            start = self._start_pos
            end = self._current_pos

            # Hide immediately BEFORE emitting signal or capturing
            self.hide()
            QApplication.processEvents()

            if start and end:
                rect = QRect(start, end).normalized()
                if rect.width() >= 15 and rect.height() >= 15:
                    region = ScreenRegion(
                        left=rect.left(),
                        top=rect.top(),
                        width=rect.width(),
                        height=rect.height(),
                    )
                    logger.info("Snip region selected: %s", region)
                    self.region_selected.emit(region)
                    return

            self.cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            QApplication.processEvents()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)


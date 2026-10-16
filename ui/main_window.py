"""
Modern dark-themed glassmorphic HUD Main Window for OmniAssist.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QKeyEvent, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
)

from ai.provider import OutputFormat
from logging_service.logger import get_logger

logger = get_logger("ui.main_window")


HUD_STYLESHEET = """
QWidget#HUDContainer {
    background-color: #12141a;
    border: 1px solid #2a2e3d;
    border-radius: 12px;
}

QLabel {
    color: #e5e7eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

QLabel#AppBadge {
    background-color: #1e2230;
    color: #93c5fd;
    border: 1px solid #3b82f6;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#StatusBadge {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QPlainTextEdit {
    background-color: #181b24;
    color: #f9fafb;
    border: 1px solid #2d3345;
    border-radius: 8px;
    padding: 10px;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
    selection-background-color: #4f46e5;
}

QPlainTextEdit:focus {
    border: 1px solid #6366f1;
}

QComboBox {
    background-color: #1e2230;
    color: #e5e7eb;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QComboBox::drop-down {
    border: none;
}

QPushButton {
    background-color: #272c3d;
    color: #f3f4f6;
    border: 1px solid #3b4259;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #32394e;
    border-color: #4e5673;
}

QPushButton:pressed {
    background-color: #1f2331;
}

QPushButton#PrimaryButton {
    background-color: #4f46e5;
    color: #ffffff;
    border: 1px solid #6366f1;
}

QPushButton#PrimaryButton:hover {
    background-color: #4338ca;
    border-color: #818cf8;
}

QPushButton#SecondaryButton {
    background-color: transparent;
    border: 1px solid #374151;
    color: #9ca3af;
}

QPushButton#SecondaryButton:hover {
    background-color: #1e2230;
    color: #f3f4f6;
}
"""


class MainWindow(QWidget):
    """
    Main Floating HUD window providing prompt preview, mode selection, and trigger controls.
    """

    generate_requested = Signal(str, str)  # (prompt_text, format_mode)
    capture_region_requested = Signal()
    capture_screen_requested = Signal()
    settings_requested = Signal()
    dismiss_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._drag_position = QPoint()

        self.resize(680, 480)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Central container widget
        container = QFrame(self)
        container.setObjectName("HUDContainer")
        container.setStyleSheet(HUD_STYLESHEET)

        # Subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(Qt.GlobalColor.black)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Top Bar
        top_bar = QHBoxLayout()
        title_label = QLabel("✨ OmniAssist")
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.app_badge = QLabel("Target: None")
        self.app_badge.setObjectName("AppBadge")

        self.status_badge = QLabel("IDLE")
        self.status_badge.setObjectName("StatusBadge")

        top_bar.addWidget(title_label)
        top_bar.addSpacing(8)
        top_bar.addWidget(self.app_badge)
        top_bar.addSpacing(6)
        top_bar.addWidget(self.status_badge)
        top_bar.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setObjectName("SecondaryButton")
        btn_close.clicked.connect(self.hide_hud)
        top_bar.addWidget(btn_close)

        layout.addLayout(top_bar)

        # Question / Prompt Editor
        self.prompt_editor = QPlainTextEdit()
        self.prompt_editor.setPlaceholderText(
            "Selected text or captured context will appear here automatically.\n"
            "You can also freely type or edit your instructions here..."
        )
        layout.addWidget(self.prompt_editor, stretch=1)

        # Bottom Bar: Mode selector and action buttons
        bottom_bar = QHBoxLayout()

        lbl_format = QLabel("Format:")
        bottom_bar.addWidget(lbl_format)

        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Auto Detect",
            "Code Only",
            "Multiple Choice",
            "Theory / Explanation",
            "JSON Object",
            "Short Answer",
        ])
        bottom_bar.addWidget(self.format_combo)

        bottom_bar.addSpacing(10)

        btn_screen = QPushButton("📷 Read Screen")
        btn_screen.setToolTip("Capture full screen photo and solve via Gemini Vision")
        btn_screen.clicked.connect(self.capture_screen_requested.emit)
        bottom_bar.addWidget(btn_screen)

        btn_snip = QPushButton("✂ Snip Region")
        btn_snip.clicked.connect(self.capture_region_requested.emit)
        bottom_bar.addWidget(btn_snip)

        btn_settings = QPushButton("⚙")
        btn_settings.setToolTip("Configure Settings")
        btn_settings.setObjectName("SecondaryButton")
        btn_settings.clicked.connect(self.settings_requested.emit)
        bottom_bar.addWidget(btn_settings)

        bottom_bar.addStretch()

        self.btn_generate = QPushButton("⚡ Generate Answer")
        self.btn_generate.setObjectName("PrimaryButton")
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        bottom_bar.addWidget(self.btn_generate)

        layout.addLayout(bottom_bar)
        outer_layout.addWidget(container)

    def set_target_app(self, app_name: str) -> None:
        self.app_badge.setText(f"Target: {app_name}")

    def set_status(self, status: str) -> None:
        self.status_badge.setText(status.upper())

    def set_prompt_text(self, text: str) -> None:
        self.prompt_editor.setPlainText(text)

    def get_prompt_text(self) -> str:
        return self.prompt_editor.toPlainText().strip()

    def get_selected_format(self) -> OutputFormat:
        idx = self.format_combo.currentIndex()
        mapping = [
            OutputFormat.AUTO,
            OutputFormat.CODE,
            OutputFormat.MULTIPLE_CHOICE,
            OutputFormat.THEORY,
            OutputFormat.JSON,
            OutputFormat.SHORT_ANSWER,
        ]
        return mapping[idx] if idx < len(mapping) else OutputFormat.AUTO

    def _on_generate_clicked(self) -> None:
        text = self.get_prompt_text()
        fmt = self.get_selected_format().value
        self.generate_requested.emit(text, fmt)

    def center_on_screen(self) -> None:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 3
            self.move(x, y)

    def show_hud(self) -> None:
        self.center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.prompt_editor.setFocus()

    def hide_hud(self) -> None:
        self.hide()
        self.dismiss_requested.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Escape dismisses the HUD."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide_hud()
        elif event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.ControlModifier or event.modifiers() & Qt.KeyboardModifier.MetaModifier):
            self._on_generate_clicked()
        else:
            super().keyPressEvent(event)

    # Window dragging support for frameless window
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

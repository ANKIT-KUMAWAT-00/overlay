"""
Modern answer presentation window with copy, insert, and syntax validation feedback.
"""

from __future__ import annotations

from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
)

from ai.response_validator import ValidationResult
from logging_service.logger import get_logger

logger = get_logger("ui.answer_window")


ANSWER_STYLESHEET = """
QWidget#AnswerContainer {
    background-color: #12141a;
    border: 1px solid #2a2e3d;
    border-radius: 12px;
}

QLabel {
    color: #e5e7eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

QLabel#SuccessBadge {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#LatencyBadge {
    background-color: #1e2230;
    color: #9ca3af;
    border: 1px solid #374151;
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
}

QLabel#WarningBanner {
    background-color: #451a03;
    color: #fcd34d;
    border: 1px solid #b45309;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}

QPlainTextEdit {
    background-color: #181b24;
    color: #f3f4f6;
    border: 1px solid #2d3345;
    border-radius: 8px;
    padding: 10px;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
    selection-background-color: #4f46e5;
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

QPushButton#PrimaryButton {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #10b981;
}

QPushButton#PrimaryButton:hover {
    background-color: #047857;
    border-color: #34d399;
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


class AnswerWindow(QWidget):
    """
    HUD window for reviewing and acting on the generated AI answer.
    """

    copy_requested = Signal(str)
    insert_requested = Signal(str)
    regenerate_requested = Signal()
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
        self.target_app_name = "Target Application"

        self.resize(700, 520)
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame(self)
        container.setObjectName("AnswerContainer")
        container.setStyleSheet(ANSWER_STYLESHEET)

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
        title_label = QLabel("✨ Solution Ready")
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.success_badge = QLabel("VALIDATED")
        self.success_badge.setObjectName("SuccessBadge")

        self.latency_badge = QLabel("0ms")
        self.latency_badge.setObjectName("LatencyBadge")

        top_bar.addWidget(title_label)
        top_bar.addSpacing(8)
        top_bar.addWidget(self.success_badge)
        top_bar.addSpacing(6)
        top_bar.addWidget(self.latency_badge)
        top_bar.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setObjectName("SecondaryButton")
        btn_close.clicked.connect(self.hide_window)
        top_bar.addWidget(btn_close)

        layout.addLayout(top_bar)

        # Warning banner (hidden by default)
        self.warning_banner = QLabel("")
        self.warning_banner.setObjectName("WarningBanner")
        self.warning_banner.setWordWrap(True)
        self.warning_banner.hide()
        layout.addWidget(self.warning_banner)

        # Answer content text area
        self.answer_viewer = QPlainTextEdit()
        self.answer_viewer.setReadOnly(False)  # User can make final tweaks before insert!
        layout.addWidget(self.answer_viewer, stretch=1)

        # Bottom actions
        bottom_bar = QHBoxLayout()

        self.btn_copy = QPushButton("📋 Copy to Clipboard")
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        bottom_bar.addWidget(self.btn_copy)

        self.btn_code_only = QPushButton("💻 Code Only")
        self.btn_code_only.setToolTip("Strip problem analysis and complexity commentary, keeping only pure code")
        self.btn_code_only.clicked.connect(self._on_code_only_clicked)
        bottom_bar.addWidget(self.btn_code_only)

        self.btn_insert = QPushButton(f"⚡ Insert into {self.target_app_name} (⌥+Enter)")
        self.btn_insert.setObjectName("PrimaryButton")
        self.btn_insert.clicked.connect(self._on_insert_clicked)
        bottom_bar.addWidget(self.btn_insert)

        bottom_bar.addStretch()

        btn_regen = QPushButton("↺ Retry")
        btn_regen.setObjectName("SecondaryButton")
        btn_regen.clicked.connect(self.regenerate_requested.emit)
        bottom_bar.addWidget(btn_regen)

        layout.addLayout(bottom_bar)
        outer_layout.addWidget(container)

    def display_answer(
        self,
        answer_text: str,
        target_app: str = "Target App",
        latency_ms: float = 0.0,
        validation: Optional[ValidationResult] = None,
    ) -> None:
        """Populates the window with answer, metrics, and validation alerts."""
        self.target_app_name = target_app
        self.btn_insert.setText(f"⚡ Insert into {target_app} (⌥+Enter)")
        self.answer_viewer.setPlainText(answer_text)
        self.latency_badge.setText(f"{int(latency_ms)}ms" if latency_ms > 0 else "")

        if validation and validation.warnings:
            self.warning_banner.setText("Notice: " + "; ".join(validation.warnings))
            self.warning_banner.show()
        else:
            self.warning_banner.hide()

        self.center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()

    def center_on_screen(self) -> None:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 3
            self.move(x, y)

    def _on_copy_clicked(self) -> None:
        text = self.answer_viewer.toPlainText()
        self.copy_requested.emit(text)
        self.btn_copy.setText("✓ Copied!")
        QTimer.singleShot(2000, lambda: self.btn_copy.setText("📋 Copy to Clipboard"))

    def _on_code_only_clicked(self) -> None:
        import re
        current_text = self.answer_viewer.toPlainText()
        embedded = re.findall(r"```(?:[a-zA-Z0-9_\-\.\+#]+)?\n([\s\S]*?)\n```", current_text)
        if embedded:
            largest = max(embedded, key=len).strip()
            self.answer_viewer.setPlainText(largest)
            self.btn_code_only.setText("✓ Extracted!")
            QTimer.singleShot(1500, lambda: self.btn_code_only.setText("💻 Code Only"))
        else:
            # If no code fences, check if there are markdown headers to strip
            lines = current_text.splitlines()
            cleaned_lines = [l for l in lines if not l.strip().startswith("###") and not l.strip().startswith("**Time Complexity") and not l.strip().startswith("*   **")]
            self.answer_viewer.setPlainText("\n".join(cleaned_lines).strip())
            self.btn_code_only.setText("✓ Cleaned!")
            QTimer.singleShot(1500, lambda: self.btn_code_only.setText("💻 Code Only"))

    def _on_insert_clicked(self) -> None:
        text = self.answer_viewer.toPlainText()
        self.insert_requested.emit(text)
        self.hide_window()

    def hide_window(self) -> None:
        self.hide()
        self.dismiss_requested.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_window()
        elif event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self._on_insert_clicked()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

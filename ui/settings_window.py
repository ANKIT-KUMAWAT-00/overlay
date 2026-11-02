"""
Settings dialog for configuring Gemini API credentials, models, shortcuts, and delivery.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)

from config.settings import AppSettings, get_settings
from security.credential_store import CredentialStore
from ai.gemini_provider import GeminiProvider
from platforms import exclude_window_from_screen_capture
from logging_service.logger import get_logger

logger = get_logger("ui.settings_window")

SETTINGS_STYLESHEET = """
QDialog {
    background-color: #161821;
    color: #e5e7eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

QGroupBox {
    background-color: #1c1f2b;
    border: 1px solid #2e3447;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #818cf8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}

QLabel {
    color: #d1d5db;
    font-size: 12px;
}

QLineEdit {
    background-color: #12141a;
    color: #f9fafb;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
}

QComboBox {
    background-color: #12141a;
    color: #f9fafb;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

QCheckBox {
    color: #e5e7eb;
    font-size: 12px;
}

QPushButton {
    background-color: #272c3d;
    color: #f3f4f6;
    border: 1px solid #3b4259;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #32394e;
    border-color: #4e5673;
}

QPushButton#SaveButton {
    background-color: #4f46e5;
    color: #ffffff;
    border: 1px solid #6366f1;
}

QPushButton#SaveButton:hover {
    background-color: #4338ca;
}
"""


class SettingsWindow(QDialog):
    """Configuration modal dialog."""

    settings_saved = Signal(AppSettings)

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OmniAssist Settings")
        self.setFixedSize(540, 560)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        self.settings = get_settings()
        self.cred_store = CredentialStore()
        self._init_ui()
        self._load_values()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        title = QLabel("⚙ Assistant Preferences")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 1. API Credentials Group
        grp_api = QGroupBox("Google Gemini Intelligence")
        api_layout = QVBoxLayout(grp_api)

        key_row = QHBoxLayout()
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_api_key.setPlaceholderText("Enter Google Gemini API Key...")

        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedWidth(36)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)

        key_row.addWidget(self.edit_api_key)
        key_row.addWidget(self.btn_toggle_key)
        api_layout.addLayout(key_row)

        cred_actions = QHBoxLayout()
        self.lbl_key_status = QLabel("Keyring Status: Checking...")
        self.lbl_key_status.setStyleSheet("color: #9ca3af; font-size: 11px;")
        cred_actions.addWidget(self.lbl_key_status)
        cred_actions.addStretch()

        btn_test = QPushButton("Test API Connection")
        btn_test.clicked.connect(self._test_connection)
        cred_actions.addWidget(btn_test)
        api_layout.addLayout(cred_actions)

        # Model selection
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Default Model:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
        model_row.addWidget(self.combo_model)
        model_row.addStretch()
        api_layout.addLayout(model_row)

        layout.addWidget(grp_api)

        # 2. Global Shortcuts Group
        grp_shortcuts = QGroupBox("Keyboard Shortcuts")
        sc_layout = QFormLayout(grp_shortcuts)
        self.edit_sc_activate = QLineEdit()
        self.edit_sc_deliver = QLineEdit()
        sc_layout.addRow("Activation Shortcut:", self.edit_sc_activate)
        sc_layout.addRow("Delivery Shortcut:", self.edit_sc_deliver)
        layout.addWidget(grp_shortcuts)

        # 3. Delivery & Automation Group
        grp_delivery = QGroupBox("Delivery & Automation")
        del_layout = QVBoxLayout(grp_delivery)
        self.chk_auto_copy = QCheckBox("Automatically copy generated answer to clipboard")
        self.chk_auto_insert = QCheckBox("Automatically insert answer into active application (direct paste)")
        del_layout.addWidget(self.chk_auto_copy)
        del_layout.addWidget(self.chk_auto_insert)
        layout.addWidget(grp_delivery)

        # Bottom Action Buttons
        layout.addStretch()
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("SaveButton")
        btn_save.clicked.connect(self._save_settings)
        btn_bar.addWidget(btn_save)

        layout.addLayout(btn_bar)

    def _toggle_key_visibility(self) -> None:
        if self.edit_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🔒")
        else:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁")

    def _load_values(self) -> None:
        # Load API key
        current_key = self.cred_store.get_api_key()
        if current_key:
            self.edit_api_key.setText(current_key)
            self.lbl_key_status.setText(f"Status: Configured ({self.cred_store.mask_key(current_key)})")
        else:
            self.lbl_key_status.setText("Status: No key saved in OS credential store")

        # Model
        idx = self.combo_model.findText(self.settings.ai.model_name)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)

        # Shortcuts
        self.edit_sc_activate.setText(self.settings.shortcuts.activation_shortcut)
        self.edit_sc_deliver.setText(self.settings.shortcuts.delivery_shortcut)

        # Delivery
        self.chk_auto_copy.setChecked(self.settings.delivery.auto_copy_to_clipboard)
        self.chk_auto_insert.setChecked(self.settings.delivery.auto_insert_to_active_app)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        exclude_window_from_screen_capture(self)

    def _test_connection(self) -> None:
        key = self.edit_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "API Test", "Please enter a Gemini API Key to test.")
            return

        provider = GeminiProvider(api_key=key, model_name=self.combo_model.currentText())
        ok = provider.health_check()
        if ok:
            QMessageBox.information(self, "API Test", "✓ Gemini API connection test succeeded!")
        else:
            QMessageBox.critical(self, "API Test", "✕ Gemini API connection test failed. Please verify your key.")

    def _save_settings(self) -> None:
        key = self.edit_api_key.text().strip()
        if key:
            self.cred_store.store_api_key(key)

        self.settings.ai.model_name = self.combo_model.currentText()
        self.settings.shortcuts.activation_shortcut = self.edit_sc_activate.text().strip()
        self.settings.shortcuts.delivery_shortcut = self.edit_sc_deliver.text().strip()
        self.settings.delivery.auto_copy_to_clipboard = self.chk_auto_copy.isChecked()
        self.settings.delivery.auto_insert_to_active_app = self.chk_auto_insert.isChecked()

        self.settings.save_to_file()
        self.settings_saved.emit(self.settings)
        self.accept()

"""
Master PySide6 Application Coordinator integrating Lifecycle, State Machine, Orchestrator, and GUI.
"""

from __future__ import annotations

import sys
from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication

from config.settings import AppSettings, get_settings
from app.state_machine import AssistantStateMachine, AssistantState
from app.lifecycle import LifecycleManager
from core.orchestrator import AssistantOrchestrator
from capture.question_capture import CapturedQuestion, CaptureMethod
from delivery.answer_delivery import DeliveryResult
from ai.response_validator import ValidationResult
from core.recovery_manager import RecoveryPlan
from ui.tray_manager import TrayManager
from ui.main_window import MainWindow
from ui.answer_window import AnswerWindow
from ui.settings_window import SettingsWindow
from logging_service.logger import get_logger

logger = get_logger("app.application")


class OmniAssistantApplication(QObject):
    """
    Top-level application container coordinating the GUI, background services,
    and state transitions.
    """

    # Thread-safe Qt signals for cross-thread orchestrator callbacks
    sig_status_updated = Signal(str)
    sig_question_captured = Signal(object)
    sig_answer_ready = Signal(str, object)
    sig_delivery_finished = Signal(object)
    sig_recovery_triggered = Signal(object)

    # Thread-safe Qt signals for pynput background hotkey callbacks
    sig_hotkey_activate = Signal()
    sig_hotkey_deliver = Signal()
    sig_hotkey_capture = Signal()
    sig_hotkey_cancel = Signal()

    def __init__(self, qapp: QApplication, settings: Optional[AppSettings] = None) -> None:
        super().__init__()
        self.qapp = qapp
        self.settings = settings or get_settings()

        # Prevent application from exiting when windows are closed (runs in background tray)
        self.qapp.setQuitOnLastWindowClosed(False)

        # Core subsystems
        self.state_machine = AssistantStateMachine()
        self.lifecycle = LifecycleManager(self.settings)
        self.orchestrator = AssistantOrchestrator(settings=self.settings)

        # GUI Components
        self.tray_manager = TrayManager()
        self.main_window = MainWindow()
        self.answer_window = AnswerWindow()
        self.settings_window = SettingsWindow()

        # Wire subsystems
        self._wire_signals()
        self._bind_orchestrator_callbacks()
        self._setup_shortcuts()

    def _wire_signals(self) -> None:
        """Connects GUI events and internal Qt signals."""
        # Hotkey cross-thread signals
        self.sig_hotkey_activate.connect(self.trigger_activation)
        self.sig_hotkey_deliver.connect(self._on_delivery_hotkey)
        self.sig_hotkey_capture.connect(self.trigger_screen_capture)
        self.sig_hotkey_cancel.connect(self._on_cancel_hotkey)

        # Tray signals
        self.tray_manager.activate_requested.connect(self.trigger_activation)
        self.tray_manager.open_hud_requested.connect(self.open_hud)
        self.tray_manager.capture_region_requested.connect(self.trigger_screen_capture)
        self.tray_manager.settings_requested.connect(self.open_settings)
        self.tray_manager.quit_requested.connect(self.quit_application)

        # Main HUD signals
        self.main_window.generate_requested.connect(self._on_generate_requested)
        self.main_window.capture_screen_requested.connect(self.trigger_screen_capture)
        self.main_window.capture_region_requested.connect(self.trigger_screen_capture)
        self.main_window.settings_requested.connect(self.open_settings)
        self.main_window.dismiss_requested.connect(self._on_hud_dismissed)

        # Answer Window signals
        self.answer_window.copy_requested.connect(self._on_copy_requested)
        self.answer_window.insert_requested.connect(self._on_insert_requested)
        self.answer_window.regenerate_requested.connect(self._on_regenerate_requested)

        # Settings Window signals
        self.settings_window.settings_saved.connect(self._on_settings_saved)

        # Cross-thread Qt signals from background orchestrator
        self.sig_status_updated.connect(self._handle_status_update)
        self.sig_question_captured.connect(self._handle_question_captured)
        self.sig_answer_ready.connect(self._handle_answer_ready)
        self.sig_delivery_finished.connect(self._handle_delivery_finished)
        self.sig_recovery_triggered.connect(self._handle_recovery_triggered)

    def _bind_orchestrator_callbacks(self) -> None:
        """Redirects background worker callbacks into Qt signal dispatcher."""
        self.orchestrator.on_status_update = lambda msg: self.sig_status_updated.emit(msg)
        self.orchestrator.on_question_captured = lambda q: self.sig_question_captured.emit(q)
        self.orchestrator.on_answer_ready = lambda ans, val: self.sig_answer_ready.emit(ans, val)
        self.orchestrator.on_delivery_finished = lambda res: self.sig_delivery_finished.emit(res)
        self.orchestrator.on_recovery_triggered = lambda plan: self.sig_recovery_triggered.emit(plan)

    def _setup_shortcuts(self) -> None:
        """Binds global keyboard hotkeys using thread-safe Qt signals."""
        self.lifecycle.shortcuts.on_activate = lambda: self.sig_hotkey_activate.emit()
        self.lifecycle.shortcuts.on_deliver = lambda: self.sig_hotkey_deliver.emit()
        self.lifecycle.shortcuts.on_capture_screen = lambda: self.sig_hotkey_capture.emit()
        self.lifecycle.shortcuts.on_cancel = lambda: self.sig_hotkey_cancel.emit()

    def start(self) -> None:
        """Starts background lifecycle, shows system tray, and presents HUD."""
        logger.info("Starting OmniAssist Application...")
        self.lifecycle.startup()
        if self.settings.ui.show_tray_icon:
            self.tray_manager.show()
        self.main_window.set_status("READY")
        self.main_window.show_hud()

    def quit_application(self) -> None:
        """Shuts down all threads, shortcuts, and terminates application cleanly."""
        logger.info("Quitting OmniAssist Application...")
        self.orchestrator.cancel()
        self.lifecycle.shutdown()
        self.qapp.quit()

    @Slot()
    def trigger_activation(self) -> None:
        """Triggered via global shortcut: captures context, scans screen if needed, and queries Gemini."""
        import time
        logger.info("Global activation triggered on MainThread.")
        try:
            self.state_machine.transition_to(AssistantState.ACTIVATING)
        except Exception:
            pass

        # 1. Detect target active app BEFORE showing HUD so target app is remembered accurately
        app_info = self.orchestrator.app_detector.detect_active_application()
        target_name = app_info.name or "Active Application"
        self.main_window.set_target_app(target_name)
        self.answer_window.target_app_name = target_name

        # 2. Hide HUD if already visible so screenshot captures background screen cleanly
        if self.main_window.isVisible():
            self.main_window.hide()
            time.sleep(0.08)

        # 3. Capture context: tries Selection -> Accessibility -> Fullscreen Vision
        try:
            captured = self.orchestrator.capture_service.capture(
                method=CaptureMethod.SMART,
                include_vision=True,
            )
        except Exception as exc:
            logger.warning("Context capture encountered notice: %s", exc)
            captured = CapturedQuestion(text="", method=CaptureMethod.MANUAL)

        # 4. Process captured context
        fmt = self.main_window.get_selected_format()

        if captured.image_bytes and len(captured.image_bytes) > 0:
            self.main_window.set_status("SCANNING")
            self.main_window.set_prompt_text("📷 Screen captured. Scanning question & generating answer via Gemini...")
            self.main_window.show_hud()
            # Send screenshot to Gemini Vision
            self.orchestrator.run_interaction_async(
                method=CaptureMethod.FULLSCREEN_VISION,
                manual_prompt=captured.text,
                format_preference=fmt,
                include_vision=True,
                image_bytes=captured.image_bytes,
                image_mime_type=captured.image_mime_type,
            )
            return

        elif captured.text and captured.text.strip():
            self.main_window.set_status("GENERATING")
            self.main_window.set_prompt_text(captured.text)
            self.main_window.show_hud()
            # Send selected text to Gemini
            self.orchestrator.run_interaction_async(
                manual_prompt=captured.text.strip(),
                format_preference=fmt,
            )
            return

        # If completely empty, open HUD for manual prompt
        self.main_window.set_status("READY")
        self.main_window.set_prompt_text("")
        self.main_window.show_hud()

    @Slot()
    def open_hud(self) -> None:
        """Opens Main HUD window."""
        self.main_window.show_hud()

    @Slot()
    def open_settings(self) -> None:
        """Opens Settings dialog."""
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    @Slot()
    def trigger_screen_capture(self) -> None:
        """Hides HUD, captures screen photo, and sends to Gemini Vision."""
        self.main_window.hide_hud()
        QTimer.singleShot(150, self._run_screen_vision)

    def _run_screen_vision(self) -> None:
        self.main_window.set_status("SCANNING")
        self.main_window.set_prompt_text("📷 Screen captured. Scanning question & generating answer via Gemini...")
        self.main_window.show_hud()
        self.orchestrator.run_interaction_async(
            method=CaptureMethod.FULLSCREEN_VISION,
            include_vision=True,
        )

    @Slot(str, str)
    def _on_generate_requested(self, prompt: str, format_mode: str) -> None:
        """Initiates background generation from user HUD."""
        self.main_window.set_status("GENERATING")
        try:
            self.state_machine.transition_to(AssistantState.GENERATING)
        except Exception:
            pass

        from ai.provider import OutputFormat
        fmt = OutputFormat(format_mode)
        self.orchestrator.run_interaction_async(
            manual_prompt=prompt,
            format_preference=fmt,
        )

    @Slot()
    def _on_delivery_hotkey(self) -> None:
        """Global shortcut to deliver active answer when user presses Option + Enter."""
        logger.info("Delivery hotkey (Option+Enter) triggered.")
        if self.answer_window.isVisible():
            text = self.answer_window.answer_viewer.toPlainText()
            self._on_insert_requested(text)
        elif self.orchestrator.recovery_manager.preserved_state.generated_answer:
            text = self.orchestrator.recovery_manager.preserved_state.generated_answer
            self._on_insert_requested(text)
        else:
            self.tray_manager.show_message("OmniAssist", "No answer available yet to insert.")

    @Slot()
    def _on_cancel_hotkey(self) -> None:
        """Global shortcut to cancel active task / dismiss windows."""
        self.orchestrator.cancel()
        self.main_window.hide_hud()
        self.answer_window.hide_window()
        self.state_machine.reset_to_idle()

    @Slot(str)
    def _on_copy_requested(self, text: str) -> None:
        self.orchestrator.delivery_coordinator.clipboard.copy(text)
        self.tray_manager.show_message("OmniAssist", "Answer copied to clipboard.")

    @Slot(str)
    def _on_insert_requested(self, text: str) -> None:
        """Inserts answer into previous application and copies to clipboard."""
        if not text:
            return
        self.answer_window.hide_window()
        target_app = self.answer_window.target_app_name
        logger.info("Scheduling insertion into '%s' in 150ms...", target_app)

        def do_insert():
            res = self.orchestrator.delivery_coordinator.deliver(
                answer_text=text,
                target_app=target_app,
                force_insert=True,
            )
            if res.success:
                self.tray_manager.show_message("OmniAssist", f"✓ Inserted answer into {target_app}")
            else:
                self.tray_manager.show_message("OmniAssist", "Clipboard copied (paste manually via ⌘V)")

        # 150ms delay lets macOS window server refocus the target application
        QTimer.singleShot(150, do_insert)

    @Slot()
    def _on_regenerate_requested(self) -> None:
        self.answer_window.hide_window()
        self.main_window.show_hud()

    @Slot()
    def _on_hud_dismissed(self) -> None:
        self.state_machine.reset_to_idle()

    @Slot(object)
    def _on_settings_saved(self, new_settings: AppSettings) -> None:
        self.settings = new_settings
        self.lifecycle.shortcuts.stop()
        self.lifecycle.shortcuts.start()
        self.orchestrator.ai_provider.set_model(new_settings.ai.model_name)
        logger.info("Applied new user settings.")

    # Cross-thread Slot Handlers
    @Slot(str)
    def _handle_status_update(self, status: str) -> None:
        self.main_window.set_status(status[:18])

    @Slot(object)
    def _handle_question_captured(self, captured: CapturedQuestion) -> None:
        if captured.text:
            self.main_window.set_prompt_text(captured.text)
        self.main_window.set_target_app(captured.source_app)

    @Slot(str, object)
    def _handle_answer_ready(self, answer: str, validation: ValidationResult) -> None:
        self.main_window.hide_hud()
        app_name = self.orchestrator.recovery_manager.preserved_state.target_app or "Active Application"
        self.answer_window.display_answer(
            answer_text=answer,
            target_app=app_name,
            validation=validation,
        )
        try:
            self.state_machine.transition_to(AssistantState.READY)
        except Exception:
            pass

    @Slot(object)
    def _handle_delivery_finished(self, result: DeliveryResult) -> None:
        if result.success:
            self.state_machine.reset_to_idle()

    @Slot(object)
    def _handle_recovery_triggered(self, plan: RecoveryPlan) -> None:
        self.main_window.set_status("ERROR")
        if plan.action == plan.action.OPEN_SETTINGS:
            self.open_settings()
        elif plan.user_message:
            self.tray_manager.show_message("OmniAssist Notice", plan.user_message)

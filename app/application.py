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
from capture.screen_capture import ScreenRegion
from ui.tray_manager import TrayManager
from ui.main_window import MainWindow
from ui.answer_window import AnswerWindow
from ui.settings_window import SettingsWindow
from ui.snipping_overlay import SnippingOverlay
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
        self.snipping_overlay = SnippingOverlay()

        # Ensure assistant windows are always hidden before any screen capture
        self.orchestrator.capture_service.pre_capture_hook = self._hide_all_windows

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
        self.tray_manager.capture_region_requested.connect(self.trigger_region_snip)
        self.tray_manager.settings_requested.connect(self.open_settings)
        self.tray_manager.quit_requested.connect(self.quit_application)

        # Main HUD signals
        self.main_window.generate_requested.connect(self._on_generate_requested)
        self.main_window.capture_screen_requested.connect(self.trigger_screen_capture)
        self.main_window.capture_region_requested.connect(self.trigger_region_snip)
        self.main_window.settings_requested.connect(self.open_settings)
        self.main_window.dismiss_requested.connect(self._on_hud_dismissed)

        # Snipping Overlay signals
        self.snipping_overlay.region_selected.connect(self._on_region_selected)
        self.snipping_overlay.cancelled.connect(self._on_snip_cancelled)

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
        """Starts background lifecycle and presents tray icon without obstructing the workspace."""
        logger.info("Starting OmniAssist Application...")
        self.lifecycle.startup()
        if self.settings.ui.show_tray_icon:
            self.tray_manager.show()
            self.tray_manager.show_message(
                "OmniAssist AI Ready",
                "Listening for shortcuts. Press ⌘+Shift+Z to activate or ⌘+Shift+S to capture screen.",
            )
        self.main_window.set_status("READY")

    def quit_application(self) -> None:
        """Shuts down all threads, shortcuts, and terminates application cleanly."""
        logger.info("Quitting OmniAssist Application...")
        self.orchestrator.cancel()
        self.lifecycle.shutdown()
        self.qapp.quit()

    @Slot()
    def _hide_all_windows(self) -> bool:
        """
        Hides all assistant windows and flushes the Qt event queue.
        Ensures none of OmniAssist's UI elements appear in screen captures.
        """
        had_visible = False
        windows_to_check = [
            getattr(self, "main_window", None),
            getattr(self, "answer_window", None),
            getattr(self, "settings_window", None),
            getattr(self, "snipping_overlay", None),
        ]
        try:
            for widget in self.qapp.topLevelWidgets():
                if widget not in windows_to_check:
                    windows_to_check.append(widget)
        except Exception:
            pass

        for win in windows_to_check:
            if win is not None and hasattr(win, "isVisible") and win.isVisible():
                had_visible = True
                win.hide()

        # Flush Qt event queue so the native window server orders out immediately
        self.qapp.processEvents()
        return had_visible

    @Slot()
    def trigger_activation(self) -> None:
        """Triggered via global shortcut: captures context, scans screen if needed, and queries Gemini."""
        logger.info("Global activation triggered on MainThread.")
        try:
            self.state_machine.transition_to(AssistantState.ACTIVATING)
        except Exception:
            pass

        # 1. Detect target active app BEFORE hiding windows so target app is remembered accurately
        app_info = self.orchestrator.app_detector.detect_active_application()
        target_name = app_info.name or "Active Application"
        self.main_window.set_target_app(target_name)
        self.answer_window.target_app_name = target_name

        # 2. Hide ALL assistant windows so they never appear in screenshots
        had_visible = self._hide_all_windows()

        if had_visible:
            # Allow OS compositor 150ms to composite the screen without assistant windows
            QTimer.singleShot(150, self._perform_context_capture)
        else:
            self._perform_context_capture()

    def _perform_context_capture(self) -> None:
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
        """Hides all assistant windows, captures full screen, and sends to Gemini Vision."""
        logger.info("Fullscreen screen capture requested.")
        self._hide_all_windows()
        # 150ms delay for OS compositor to clear all assistant window surfaces
        QTimer.singleShot(150, self._capture_and_run_fullscreen)

    def _capture_and_run_fullscreen(self) -> None:
        try:
            screenshot = self.orchestrator.capture_service.screen_capture.capture_fullscreen()
            img_bytes = self.orchestrator.capture_service.screen_capture.image_to_bytes(
                screenshot, format="JPEG", quality=80
            )
        except Exception as exc:
            logger.error("Fullscreen capture failed: %s", exc)
            img_bytes = None

        # Display HUD only AFTER screenshot has been captured cleanly
        self.main_window.set_status("SCANNING")
        self.main_window.set_prompt_text("📷 Screen captured. Scanning question & generating answer via Gemini...")
        self.main_window.show_hud()

        fmt = self.main_window.get_selected_format()
        self.orchestrator.run_interaction_async(
            method=CaptureMethod.FULLSCREEN_VISION,
            format_preference=fmt,
            include_vision=True,
            image_bytes=img_bytes,
            image_mime_type="image/jpeg",
        )

    @Slot()
    def trigger_region_snip(self) -> None:
        """Hides assistant windows and initiates interactive region snipping overlay."""
        logger.info("Region snip requested.")
        self._hide_all_windows()
        QTimer.singleShot(120, self.snipping_overlay.start_selection)

    @Slot(object)
    def _on_region_selected(self, region: ScreenRegion) -> None:
        """Handles user selecting a region in the snipping overlay."""
        # 120ms delay allows window manager to remove overlay before region capture
        QTimer.singleShot(120, lambda: self._capture_and_run_region(region))

    def _capture_and_run_region(self, region: ScreenRegion) -> None:
        try:
            img = self.orchestrator.capture_service.screen_capture.capture_region(region)
            img_bytes = self.orchestrator.capture_service.screen_capture.image_to_bytes(
                img, format="JPEG", quality=80
            )
        except Exception as exc:
            logger.error("Region capture error: %s", exc)
            img_bytes = None

        # Present HUD with scanning feedback after capture
        self.main_window.set_status("SCANNING")
        self.main_window.set_prompt_text(f"✂ Region captured ({region.width}×{region.height} px). Scanning question & generating answer via Gemini...")
        self.main_window.show_hud()

        fmt = self.main_window.get_selected_format()
        self.orchestrator.run_interaction_async(
            method=CaptureMethod.FULLSCREEN_VISION,
            region=region,
            format_preference=fmt,
            include_vision=True,
            image_bytes=img_bytes,
            image_mime_type="image/jpeg",
        )

    @Slot()
    def _on_snip_cancelled(self) -> None:
        """Restores HUD when region snip is dismissed without selecting."""
        logger.info("Region snip cancelled.")
        self.main_window.show_hud()

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
        if hasattr(self, "snipping_overlay"):
            self.snipping_overlay.hide()
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
        if hasattr(self.orchestrator.ai_provider, "set_ssl_verify"):
            self.orchestrator.ai_provider.set_ssl_verify(new_settings.ai.ssl_verify)
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

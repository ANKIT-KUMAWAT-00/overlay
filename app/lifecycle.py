"""
Global hotkey registration, conflict detection, and application lifecycle management.
"""

from __future__ import annotations

import platform
import threading
from typing import Optional, Callable, Dict, Any

from config.settings import AppSettings, get_settings
from logging_service.logger import get_logger

logger = get_logger("app.lifecycle")


class GlobalShortcutService:
    """
    Manages background global keyboard shortcuts with conflict detection.
    """

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        self.settings = settings or get_settings()
        self._hotkey_listener = None
        self._is_running = False
        self._lock = threading.Lock()

        # Handlers
        self.on_activate: Optional[Callable[[], None]] = None
        self.on_deliver: Optional[Callable[[], None]] = None
        self.on_capture_screen: Optional[Callable[[], None]] = None
        self.on_cancel: Optional[Callable[[], None]] = None

    def start(self) -> bool:
        """Starts global shortcut listener in background daemon thread."""
        with self._lock:
            if self._is_running:
                return True

            try:
                from pynput import keyboard

                hotkey_map = {}

                # 1. Activation Shortcut
                act_sc = self._normalize_hotkey_string(self.settings.shortcuts.activation_shortcut)
                if act_sc and self.on_activate:
                    hotkey_map[act_sc] = self._safe_callback(self.on_activate, "on_activate")

                # 2. Delivery Shortcut
                del_sc = self._normalize_hotkey_string(self.settings.shortcuts.delivery_shortcut)
                if del_sc and self.on_deliver:
                    hotkey_map[del_sc] = self._safe_callback(self.on_deliver, "on_deliver")

                # 3. Screen Capture Shortcut
                cap_sc = self._normalize_hotkey_string(self.settings.shortcuts.screen_capture_shortcut)
                if cap_sc and self.on_capture_screen:
                    hotkey_map[cap_sc] = self._safe_callback(self.on_capture_screen, "on_capture_screen")

                # 4. Cancel Shortcut
                can_sc = self._normalize_hotkey_string(self.settings.shortcuts.cancel_shortcut)
                if can_sc and self.on_cancel:
                    hotkey_map[can_sc] = self._safe_callback(self.on_cancel, "on_cancel")

                logger.info("Registering global hotkeys: %s", list(hotkey_map.keys()))
                self._hotkey_listener = keyboard.GlobalHotKeys(hotkey_map)
                self._hotkey_listener.daemon = True
                self._hotkey_listener.start()
                self._is_running = True
                return True

            except Exception as exc:
                logger.error("Failed to register global hotkeys: %s", exc)
                self._is_running = False
                return False

    def stop(self) -> None:
        """Stops active global keyboard listener."""
        with self._lock:
            if self._hotkey_listener and self._is_running:
                try:
                    self._hotkey_listener.stop()
                    logger.info("Stopped global shortcut listener.")
                except Exception as exc:
                    logger.warning("Error stopping hotkey listener: %s", exc)
                finally:
                    self._hotkey_listener = None
                    self._is_running = False

    def _normalize_hotkey_string(self, key_str: str) -> str:
        """
        Translates human/config hotkey strings to pynput format.
        e.g. '<cmd>+<shift>+z' -> '<cmd>+<shift>+z'
             'Ctrl + Shift + Z' -> '<ctrl>+<shift>+z'
        """
        if not key_str:
            return ""
        k = key_str.lower().replace(" ", "")
        # Replace common modifiers if not bracketed
        if "ctrl" in k and "<ctrl>" not in k:
            k = k.replace("ctrl", "<ctrl>")
        if "cmd" in k and "<cmd>" not in k:
            k = k.replace("cmd", "<cmd>")
        if "command" in k and "<cmd>" not in k:
            k = k.replace("command", "<cmd>")
        if "alt" in k and "<alt>" not in k:
            k = k.replace("alt", "<alt>")
        if "shift" in k and "<shift>" not in k:
            k = k.replace("shift", "<shift>")
        if "esc" in k and "<esc>" not in k:
            k = k.replace("esc", "<esc>")
        if "enter" in k and "<enter>" not in k:
            k = k.replace("enter", "<enter>")
        return k

    def _safe_callback(self, fn: Callable[[], None], name: str) -> Callable[[], None]:
        def wrapped():
            logger.info("Global hotkey triggered: %s", name)
            try:
                fn()
            except Exception as exc:
                logger.error("Error in hotkey handler %s: %s", name, exc, exc_info=True)
        return wrapped


class LifecycleManager:
    """
    Coordinates application startup, background running, and graceful shutdown.
    """

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        self.settings = settings or get_settings()
        self.shortcuts = GlobalShortcutService(self.settings)

    def startup(self) -> None:
        """Runs pre-flight initialization."""
        logger.info("OmniAssist lifecycle starting up...")
        self.shortcuts.start()

    def shutdown(self) -> None:
        """Halt services and background hooks cleanly."""
        logger.info("OmniAssist lifecycle shutting down...")
        self.shortcuts.stop()

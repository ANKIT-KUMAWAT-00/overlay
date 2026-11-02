"""
macOS-specific OS integration, Accessibility checks, and Window/App introspection.
"""

from __future__ import annotations

import subprocess
import time
from typing import Optional, Dict, Any

import pyperclip

from logging_service.logger import get_logger

logger = get_logger("platforms.macos")


class MacOSPlatform:
    """macOS platform helper leveraging AppKit/PyObjC and AppleScript."""

    def __init__(self) -> None:
        self._has_pyobjc = False
        try:
            import AppKit  # noqa
            self._has_pyobjc = True
        except ImportError:
            logger.debug("PyObjC / AppKit not directly imported; using AppleScript fallback.")

    def check_accessibility_permissions(self, prompt: bool = True) -> bool:
        """
        Checks whether this application has macOS Accessibility (AX) trust.
        """
        try:
            import importlib
            app_services = importlib.import_module("ApplicationServices")
            ax_func = getattr(app_services, "AXIsProcessTrustedWithOptions", None)
            k_prompt = getattr(app_services, "kAXTrustedCheckOptionPrompt", None)
            if ax_func and k_prompt:
                options = {k_prompt: prompt} if prompt else {}
                trusted = ax_func(options)
                logger.debug("macOS AXIsProcessTrusted result: %s", trusted)
                return bool(trusted)
        except Exception:
            pass

        # Fallback check via osascript
        script = 'tell application "System Events" to get name of first process whose frontmost is true'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return res.returncode == 0

    def exclude_window_from_screen_capture(self, qwidget: Any) -> bool:
        """
        Natively excludes a PySide6 window from all screen recordings and screenshots
        using macOS AppKit NSWindowSharingNone.
        """
        try:
            import AppKit
            import objc
            from ctypes import c_void_p

            win_id = int(qwidget.winId())
            ns_view = objc.objc_object(c_void_p=win_id)
            ns_window = ns_view.window()
            if ns_window:
                ns_window.setSharingType_(AppKit.NSWindowSharingNone)
                logger.info("Successfully applied NSWindowSharingNone to window %s", qwidget)
                return True
        except Exception as exc:
            logger.debug("Failed to set NSWindowSharingNone: %s", exc)
        return False

    def get_active_app_info(self) -> Dict[str, Any]:
        """
        Retrieves active frontmost application name, bundle ID, and window title.
        """
        info: Dict[str, Any] = {
            "app_name": "Unknown",
            "bundle_id": "",
            "window_title": "",
            "pid": 0,
        }

        # Method 1: AppKit NSWorkspace
        try:
            import importlib
            app_kit = importlib.import_module("AppKit")
            ns_workspace = getattr(app_kit, "NSWorkspace", None)
            if ns_workspace:
                front_app = ns_workspace.sharedWorkspace().frontmostApplication()
                if front_app:
                    info["app_name"] = str(front_app.localizedName() or "")
                    info["bundle_id"] = str(front_app.bundleIdentifier() or "")
                    info["pid"] = int(front_app.processIdentifier() or 0)
        except Exception as exc:
            logger.debug("NSWorkspace active app lookup failed: %s", exc)

        # Method 2: AppleScript fallback/enrichment for window title
        script = """
        global frontApp, windowTitle
        set windowTitle to ""
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            try
                tell process frontApp
                    set windowTitle to name of front window
                end tell
            end try
        end tell
        return frontApp & "|||" & windowTitle
        """
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("|||")
                if len(parts) >= 1 and not info["app_name"] or info["app_name"] == "Unknown":
                    info["app_name"] = parts[0]
                if len(parts) >= 2:
                    info["window_title"] = parts[1]
        except Exception as exc:
            logger.debug("AppleScript window query failed: %s", exc)

        return info

    def get_selected_text_via_clipboard(self, restore_clipboard: bool = True) -> Optional[str]:
        """
        Simulates Cmd+C with clipboard preservation to grab user selection safely.
        """
        import pyperclip

        # 1. Save old clipboard
        old_clip = None
        if restore_clipboard:
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = None

        # 2. Clear clipboard temporarily to detect fresh copy
        sentinel = f"__omni_sentinel_{int(time.time() * 1000)}__"
        try:
            pyperclip.copy(sentinel)
        except Exception:
            pass

        # 3. Simulate Cmd+C via osascript
        script = 'tell application "System Events" to keystroke "c" using command down'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.0)
            time.sleep(0.08)  # Short delay for clipboard sync
        except Exception as exc:
            logger.warning("Keystroke simulation failed: %s", exc)

        # 4. Read result
        try:
            new_clip = pyperclip.paste()
            selected = None
            if new_clip and new_clip != sentinel:
                selected = new_clip

            # 5. Restore previous clipboard
            if restore_clipboard and old_clip is not None:
                pyperclip.copy(old_clip)

            return selected
        except Exception as exc:
            logger.warning("Clipboard read failed: %s", exc)
            return None

    def insert_text(self, text: str, method: str = "clipboard") -> bool:
        """
        Inserts text into the currently active target window.
        """
        if not text:
            return False

        if method == "clipboard":
            try:
                pyperclip.copy(text)
                time.sleep(0.05)
                script = 'tell application "System Events" to keystroke "v" using command down'
                res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.5)
                return res.returncode == 0
            except Exception as exc:
                logger.error("macOS paste injection failed: %s", exc)
                return False

        return False

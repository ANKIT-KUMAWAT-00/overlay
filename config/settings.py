"""
Application configuration schema and persistence using Pydantic.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from logging_service.logger import get_logger

logger = get_logger("config.settings")

DEFAULT_CONFIG_PATH = Path.home() / ".omniassist" / "config.json"


def get_default_activation_shortcut() -> str:
    """Returns platform-standard activation shortcut."""
    if platform.system() == "Darwin":
        return "<cmd>+<shift>+z"
    return "<ctrl>+<shift>+z"


def get_default_delivery_shortcut() -> str:
    """Returns platform-standard answer insertion shortcut."""
    if platform.system() == "Darwin":
        return "<alt>+<enter>"
    return "<alt>+<enter>"


class AISettings(BaseModel):
    """Configuration for Gemini AI provider."""
    model_name: str = Field(default="gemini-3-flash-preview", description="Gemini model identifier")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=4096, ge=128, le=32768)
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    system_instruction: str = Field(
        default=(
            "You are OmniAssist, a precise, expert AI desktop assistant. "
            "Follow the user's requested output format exactly. "
            "If code is requested, provide clean code without fluff. "
            "If an answer or option is requested, be direct and concise."
        )
    )


class ShortcutSettings(BaseModel):
    """Keybinding settings for global activation."""
    activation_shortcut: str = Field(default_factory=get_default_activation_shortcut)
    delivery_shortcut: str = Field(default_factory=get_default_delivery_shortcut)
    screen_capture_shortcut: str = Field(default="<cmd>+<shift>+s" if platform.system() == "Darwin" else "<ctrl>+<shift>+s")
    cancel_shortcut: str = Field(default="<esc>")


class CaptureSettings(BaseModel):
    """Preferences for reading context from target applications."""
    preferred_mode: str = Field(default="smart", description="'smart', 'selection', 'ocr', 'clipboard', 'manual'")
    enable_ocr_fallback: bool = True
    ocr_tesseract_cmd: Optional[str] = None
    ocr_language: str = "eng"
    preserve_indentation: bool = True
    max_context_chars: int = 12000


class DeliverySettings(BaseModel):
    """Preferences for inserting or delivering generated answers."""
    auto_copy_to_clipboard: bool = True
    auto_insert_to_active_app: bool = False
    simulate_typing_delay_ms: int = 10
    verify_target_window: bool = True


class UISettings(BaseModel):
    """GUI and appearance settings."""
    theme: str = Field(default="dark", description="'dark', 'light', 'system'")
    window_opacity: float = Field(default=0.96, ge=0.5, le=1.0)
    always_on_top: bool = True
    hud_width: int = 700
    hud_height: int = 520
    show_tray_icon: bool = True
    launch_at_startup: bool = False


def _load_env_file() -> None:
    for env_path in (Path(".env"), Path(__file__).resolve().parent.parent / ".env"):
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and not os.environ.get(k):
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env_file()


class AppSettings(BaseModel):
    """Root configuration model for OmniAssist."""
    ai: AISettings = Field(default_factory=AISettings)
    shortcuts: ShortcutSettings = Field(default_factory=ShortcutSettings)
    capture: CaptureSettings = Field(default_factory=CaptureSettings)
    delivery: DeliverySettings = Field(default_factory=DeliverySettings)
    ui: UISettings = Field(default_factory=UISettings)

    def save_to_file(self, path: Optional[Path] = None) -> bool:
        """Persists current settings to JSON file."""
        target = path or DEFAULT_CONFIG_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
            logger.info("Saved settings to %s", target)
            return True
        except Exception as exc:
            logger.error("Failed to save settings to %s: %s", target, exc)
            return False

    @classmethod
    def load_from_file(cls, path: Optional[Path] = None) -> AppSettings:
        """Loads settings from JSON file or returns defaults."""
        target = path or DEFAULT_CONFIG_PATH
        if not target.exists():
            instance = cls()
            instance.save_to_file(target)
            return instance

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = cls.model_validate(data)
        except Exception as exc:
            logger.warning("Error reading config at %s, using defaults: %s", target, exc)
            settings = cls()

        # Migrate deprecated models for default config
        if path is None and settings.ai.model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
            settings.ai.model_name = "gemini-3-flash-preview"
            settings.save_to_file(target)

        # Environment variable override for default config
        if path is None:
            env_model = os.getenv("GEMINI_MODEL")
            if env_model:
                settings.ai.model_name = env_model

        return settings


_CURRENT_SETTINGS: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Returns singleton settings instance."""
    global _CURRENT_SETTINGS
    if _CURRENT_SETTINGS is None:
        _CURRENT_SETTINGS = AppSettings.load_from_file()
    return _CURRENT_SETTINGS


def reload_settings() -> AppSettings:
    """Forces reloading settings from disk."""
    global _CURRENT_SETTINGS
    _CURRENT_SETTINGS = AppSettings.load_from_file()
    return _CURRENT_SETTINGS

"""
Unit tests for application classification and capability mapping.
"""

import pytest
from core.application_detector import ApplicationDetector, AppCategory, DetectedApplication
from core.capability_registry import CapabilityRegistry, AppCapabilities
from config.settings import AppSettings


def test_capability_registry():
    reg = CapabilityRegistry()
    ide_caps = reg.get_capabilities(AppCategory.IDE)
    assert isinstance(ide_caps, AppCapabilities)
    assert ide_caps.prefers_raw_code is True
    assert ide_caps.can_paste_text is True

    term_caps = reg.get_capabilities(AppCategory.TERMINAL)
    assert term_caps.prefers_raw_code is True

    pdf_caps = reg.get_capabilities(AppCategory.PDF_VIEWER)
    assert pdf_caps.requires_ocr_for_text is True


def test_application_detector():
    detector = ApplicationDetector()
    app = detector.detect_active_application()
    assert isinstance(app, DetectedApplication)
    assert app.name is not None
    assert isinstance(app.category, AppCategory)


def test_settings_serialization(tmp_path):
    config_file = tmp_path / "config.json"
    settings = AppSettings()
    settings.ai.model_name = "gemini-2.5-pro"
    settings.shortcuts.activation_shortcut = "<ctrl>+<shift>+z"

    saved = settings.save_to_file(config_file)
    assert saved is True
    assert config_file.exists()

    loaded = AppSettings.load_from_file(config_file)
    assert loaded.ai.model_name == "gemini-2.5-pro"
    assert loaded.shortcuts.activation_shortcut == "<ctrl>+<shift>+z"

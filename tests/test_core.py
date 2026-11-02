"""
Unit tests for application classification and capability mapping.
"""

import pytest
# pyrefly: ignore [missing-import]
from core.application_detector import ApplicationDetector, AppCategory, DetectedApplication
from core.capability_registry import CapabilityRegistry, AppCapabilities
from config.settings import AppSettings
from unittest.mock import MagicMock


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


def test_application_detector_ignores_self_process():
    detector = ApplicationDetector()
    mock_platform = MagicMock()
    detector.platform = mock_platform

    # First active app is Chrome
    mock_platform.get_active_app_info.return_value = {
        "app_name": "Google Chrome",
        "bundle_id": "com.google.Chrome",
        "window_title": "LeetCode - Online Judge",
        "pid": 1234,
    }
    app1 = detector.detect_active_application()
    assert app1.name == "Google Chrome"
    assert app1.category == AppCategory.BROWSER

    # Next foreground app becomes Python (OmniAssist)
    mock_platform.get_active_app_info.return_value = {
        "app_name": "Python",
        "bundle_id": "org.python.python",
        "window_title": "OmniAssist",
        "pid": 5678,
    }
    app2 = detector.detect_active_application()
    # It must preserve Google Chrome instead of reporting Python!
    assert app2.name == "Google Chrome"


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

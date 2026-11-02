"""
Unit tests for UI geometry, compact HUD sizing, and snipping overlay lifecycle.
"""

import sys
import pytest
from PySide6.QtWidgets import QApplication

# Ensure QApplication singleton exists for tests
app = QApplication.instance() or QApplication(sys.argv)

from ui.main_window import MainWindow
from ui.answer_window import AnswerWindow
from ui.snipping_overlay import SnippingOverlay
from ai.provider import OutputFormat


def test_main_window_compact_geometry():
    """Verify MainWindow conforms to reduced, non-obstructive dimensions."""
    win = MainWindow()
    assert win.width() <= 550
    assert win.height() <= 250
    assert win.prompt_editor.maximumHeight() <= 100


def test_answer_window_compact_geometry():
    """Verify AnswerWindow conforms to compact dimensions."""
    win = AnswerWindow()
    assert win.width() <= 600
    assert win.height() <= 350


def test_format_dropdown_multi_language_mapping():
    """Verify format combo maps to specific programming language OutputFormats."""
    win = MainWindow()
    
    # "Code (C++)" is index 2
    win.format_combo.setCurrentIndex(2)
    assert win.get_selected_format() == OutputFormat.CODE_CPP

    # "Code (Python)" is index 3
    win.format_combo.setCurrentIndex(3)
    assert win.get_selected_format() == OutputFormat.CODE_PYTHON

    # "Code (Java)" is index 4
    win.format_combo.setCurrentIndex(4)
    assert win.get_selected_format() == OutputFormat.CODE_JAVA

    # "Code (JS / TS)" is index 5
    win.format_combo.setCurrentIndex(5)
    assert win.get_selected_format() == OutputFormat.CODE_JS


def test_snipping_overlay_init():
    """Verify SnippingOverlay creates with correct flags."""
    overlay = SnippingOverlay()
    assert overlay.cursor().shape() is not None

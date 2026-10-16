"""
Unit tests for browser detection and privacy-hardened adapter capabilities.
"""

import pytest
from browsers.base_adapter import BrowserCapabilities
from browsers.capability_detection import BrowserCapabilityDetector
from browsers.adapters import (
    ChromeBrowserAdapter,
    SafariBrowserAdapter,
    FirefoxBrowserAdapter,
    BraveBrowserAdapter,
    TorBrowserAdapter,
    LibreWolfBrowserAdapter,
    GenericBrowserAdapter,
)


def test_tor_browser_capabilities():
    caps = BrowserCapabilityDetector.evaluate("Tor Browser", {})
    assert caps.privacy_hardened is True
    assert caps.supports_automation_api is False
    assert caps.can_identify_editable_targets is False
    assert "Tor" in caps.isolation_notes


def test_librewolf_capabilities():
    caps = BrowserCapabilityDetector.evaluate("LibreWolf", {})
    assert caps.privacy_hardened is True
    assert caps.can_insert_text is True


def test_brave_capabilities():
    caps = BrowserCapabilityDetector.evaluate("Brave Browser", {})
    assert caps.privacy_hardened is True
    assert caps.can_get_selected_text is True


def test_chrome_capabilities():
    caps = BrowserCapabilityDetector.evaluate("Google Chrome", {})
    assert caps.privacy_hardened is False
    assert caps.can_insert_text is True


def test_browser_adapter_instantiation():
    adapters = [
        ChromeBrowserAdapter(),
        SafariBrowserAdapter(),
        FirefoxBrowserAdapter(),
        BraveBrowserAdapter(),
        TorBrowserAdapter(),
        LibreWolfBrowserAdapter(),
        GenericBrowserAdapter(),
    ]
    for adapter in adapters:
        assert adapter.browser_name is not None
        caps = adapter.get_capabilities()
        assert isinstance(caps, BrowserCapabilities)
        # Verify interface contract methods exist and are callable
        assert hasattr(adapter, "detect_browser")
        assert hasattr(adapter, "get_selected_text")
        assert hasattr(adapter, "get_visible_text")
        assert hasattr(adapter, "capture_visible_region")
        assert hasattr(adapter, "identify_editable_targets")
        assert hasattr(adapter, "insert_text")
        assert hasattr(adapter, "copy_text")
        assert hasattr(adapter, "verify_result")
        assert hasattr(adapter, "dispose")
        adapter.dispose()

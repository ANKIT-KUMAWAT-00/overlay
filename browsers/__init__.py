"""
Browser integration and privacy-focused adapter subsystem for OmniAssist.
"""

from .base_adapter import BrowserAdapter, BrowserCapabilities
from .browser_detection import BrowserDetector
from .capability_detection import BrowserCapabilityDetector

__all__ = [
    "BrowserAdapter",
    "BrowserCapabilities",
    "BrowserDetector",
    "BrowserCapabilityDetector",
]

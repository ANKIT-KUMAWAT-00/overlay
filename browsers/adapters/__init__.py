"""
Concrete browser adapters for OmniAssist.
"""

from .generic_adapter import GenericBrowserAdapter
from .chrome_adapter import ChromeBrowserAdapter
from .safari_adapter import SafariBrowserAdapter
from .firefox_adapter import FirefoxBrowserAdapter
from .brave_adapter import BraveBrowserAdapter
from .edge_adapter import EdgeBrowserAdapter
from .tor_adapter import TorBrowserAdapter
from .librewolf_adapter import LibreWolfBrowserAdapter

__all__ = [
    "GenericBrowserAdapter",
    "ChromeBrowserAdapter",
    "SafariBrowserAdapter",
    "FirefoxBrowserAdapter",
    "BraveBrowserAdapter",
    "EdgeBrowserAdapter",
    "TorBrowserAdapter",
    "LibreWolfBrowserAdapter",
]

"""Cross-Platform Active Window Geometry Detector."""
import sys
from typing import NamedTuple

class WindowRect(NamedTuple):
    x: int
    y: int
    width: int
    height: int
    title: str
    owner: str

def get_active_window_rect() -> WindowRect:
    # Stub implementation returning mock geometry for testing
    return WindowRect(x=100, y=100, width=1280, height=800, title="Visual Studio Code", owner="Code")

"""Decoupled Delivery Strategy."""
from enum import Enum, auto

class DeliveryStrategy(Enum):
    CLIPBOARD_PASTE = auto()
    KEYSTROKE_INJECTION = auto()
    ACCESSIBILITY_SET_VALUE = auto()
    HUD_ONLY = auto()

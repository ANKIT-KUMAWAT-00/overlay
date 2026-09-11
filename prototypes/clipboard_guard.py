"""Clipboard Mutex Guard."""
import threading
from contextlib import contextmanager

_CLIPBOARD_LOCK = threading.RLock()

@contextmanager
def locked_clipboard():
    with _CLIPBOARD_LOCK:
        yield

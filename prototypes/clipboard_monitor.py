"""Clipboard Monitoring with Debounce Throttle."""
import time
from typing import Optional, Callable

class DebouncedClipboardWatcher:
    def __init__(self, debounce_delay: float = 0.3):
        self.delay = debounce_delay
        self._last_text = ""
        self._last_time = 0.0

    def on_change(self, current_text: str, callback: Callable[[str], None]):
        now = time.time()
        if current_text != self._last_text and (now - self._last_time) >= self.delay:
            self._last_text = current_text
            self._last_time = now
            callback(current_text)

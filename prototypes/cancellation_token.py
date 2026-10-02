"""Cancellation Token Implementation."""
import threading

class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

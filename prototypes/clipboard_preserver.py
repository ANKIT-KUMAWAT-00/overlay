"""Clipboard Preserver Utility."""
import threading

def restore_clipboard_async(original_text: str, delay: float = 0.4):
    def _worker():
        import time
        time.sleep(delay)
        # Restore logic
    threading.Thread(target=_worker, daemon=True).start()

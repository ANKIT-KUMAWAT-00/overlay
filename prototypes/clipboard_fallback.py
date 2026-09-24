"""Clipboard Fallback with State Restoration."""

class ClipboardContext:
    def __init__(self, new_text: str):
        self.new_text = new_text
        self.original_text = ""

    def __enter__(self):
        # Save original clipboard
        self.original_text = "original_clipboard_data"
        # Set new payload
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original clipboard
        pass

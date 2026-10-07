"""macOS NSWindowSharingNone Prototype."""

NSWindowSharingNone = 0

def exclude_nswindow_from_capture(window_id: int) -> bool:
    # Prototype AppKit setSharingType:NSWindowSharingNone
    return True

"""Windows SetWindowDisplayAffinity Prototype."""

WDA_EXCLUDEFROMCAPTURE = 0x00000011

def set_exclude_from_capture_win32(hwnd: int) -> bool:
    # Prototype ctypes call to user32.SetWindowDisplayAffinity
    return True

# Focus Management & Cursor Restoration

When OmniAssist's HUD activates, the target application loses native OS focus.
To ensure clean text insertion:
1. Capture target window handle (`HWND` on Windows, `CGWindowID` on macOS).
2. Restore target window to foreground before simulating `Cmd+V` / `Ctrl+V`.
3. Wait 50ms for the OS window manager event loop to flush focus.

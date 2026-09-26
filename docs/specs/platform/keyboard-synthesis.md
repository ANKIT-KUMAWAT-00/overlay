# Keyboard Event Synthesis Across OS

- **macOS**: `CGEventCreateKeyboardEvent` requires Accessibility trust. Option key is code 58.
- **Windows**: `SendInput` API requires `KEYEVENTF_KEYUP` pairs.
- **Wayland / Linux**: Synthetic input blocked without `ydotool` / `uinput` daemon permissions.

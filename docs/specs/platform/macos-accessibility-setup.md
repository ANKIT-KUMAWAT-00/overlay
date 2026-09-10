# macOS Accessibility Setup Guide

## System Settings Navigation
1. Open **System Settings** -> **Privacy & Security**.
2. Select **Accessibility**.
3. Toggle the switch for `OmniAssist` or terminal emulator running Python.

## Programmatic Verification (Objective-C / PyObjC)
```python
import ApplicationServices
is_trusted = ApplicationServices.AXIsProcessTrusted()
```

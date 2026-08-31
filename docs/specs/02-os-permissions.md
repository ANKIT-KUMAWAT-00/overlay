# OS Accessibility Permission Matrix

| Operating System | Permission Required | Fallback Strategy |
|---|---|---|
| macOS 13+ (Ventura+) | Accessibility API (AXIsProcessTrusted) | Interactive prompt + Settings Deep Link |
| macOS 13+ | Screen Recording (CGPreflightScreenCaptureAccess) | Window-specific capture fallback |
| Windows 10/11 | UI Automation (UIA) | Standard Win32 hook |
| Windows 10/11 | Window Affiliation | Direct BitBlt / PrintWindow |

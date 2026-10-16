# OmniAssist Standalone Packaging & Build Instructions

This guide provides instructions for compiling OmniAssist into a standalone, distribution-ready desktop binary for **macOS** and **Windows** using **PyInstaller**.

---

## 1. Prerequisites

Ensure dependencies are installed in your virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

---

## 2. Packaging for macOS (.app Bundle)

### A. One-Command Build

On macOS, build a windowed `.app` bundle that runs cleanly in the menu-bar and desktop without opening a Terminal console:

```bash
pyinstaller \
  --name "OmniAssist" \
  --windowed \
  --noconsole \
  --onedir \
  --add-data "config:config" \
  --hidden-import "PySide6" \
  --hidden-import "pynput" \
  --hidden-import "google.genai" \
  --hidden-import "PIL" \
  --hidden-import "pytesseract" \
  --osx-bundle-identifier "com.omniassist.desktop" \
  main.py
```

### B. macOS Info.plist Permissions

macOS requires declaration of Privacy & Accessibility usage descriptions in `dist/OmniAssist.app/Contents/Info.plist`:

```xml
<key>NSAppleEventsUsageDescription</key>
<string>OmniAssist requires AppleEvents permission to detect active application windows and copy selected text.</string>
<key>NSScreenCaptureUsageDescription</key>
<string>OmniAssist requires screen recording permission to snip screen regions for question context.</string>
<key>NSAccessibilityUsageDescription</key>
<string>OmniAssist uses Accessibility APIs to detect active text selection.</string>
```

### C. Codesigning & Notarization

To distribute to macOS users without Gatekeeper warnings:

```bash
# Sign the application bundle
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name (TEAMID)" dist/OmniAssist.app

# Create a DMG and notarize with Apple notarytool
xcrun notarytool submit OmniAssist.dmg --keychain-profile "AC_PASSWORD" --wait
```

---

## 3. Packaging for Windows (.exe Standalone)

### A. One-Command Build

On Windows, generate a single self-contained executable with no console window:

```powershell
pyinstaller `
  --name "OmniAssist" `
  --noconsole `
  --onefile `
  --add-data "config;config" `
  --hidden-import "PySide6" `
  --hidden-import "pynput" `
  --hidden-import "google.genai" `
  --hidden-import "keyring.backends.Windows" `
  main.py
```

### B. Output Location

The resulting binary will be in `dist/OmniAssist.exe`.

When launched, it runs in the background and places an icon in the Windows System Tray (notification area).

---

## 4. Launch at Startup Configuration

### macOS (LaunchAgent)

Place a `.plist` file in `~/Library/LaunchAgents/com.omniassist.desktop.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omniassist.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/OmniAssist.app/Contents/MacOS/OmniAssist</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

Activate it:
```bash
launchctl load ~/Library/LaunchAgents/com.omniassist.desktop.plist
```

### Windows (Startup Shortcut)

Create a shortcut to `OmniAssist.exe` inside:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

---

## 5. Troubleshooting Packaged Builds

1. **PySide6 / Qt plugins missing**:
   Add `--collect-submodules PySide6` or `--collect-data PySide6`.
2. **Keyring backend missing in bundle**:
   Explicitly add `--hidden-import keyring.backends.macOS` (macOS) or `--hidden-import keyring.backends.Windows` (Windows).
3. **SSL Certificate verification error**:
   Add `--collect-data certifi` to ensure Mozilla CA certificates are bundled for HTTPS requests to the Gemini API.

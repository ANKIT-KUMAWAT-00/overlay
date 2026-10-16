# OmniAssist: Universal Python-Based AI Desktop Assistant

A production-grade, modular, cross-platform AI computer-interaction assistant built entirely in **Python**. Powered by **Google Gemini AI**, OmniAssist seamlessly captures context from active desktop applications (via selection hooks, accessibility trees, screen-region OCR, and multimodal vision), formulates targeted responses, rigorously validates syntax and completeness, and injects answers directly into user workflows with zero data loss.

---

## 1. Architectural Overview

OmniAssist implements a decoupled, event-driven, capability-aware layered architecture where the user interface, finite state machine, AI reasoning engine, and operating system automation layers are cleanly isolated.

```
┌─────────────────────────────────────────────────────────────────┐
│               Modern Dark Glassmorphic PySide6 HUD              │
│        (Question Preview, Code Viewer, Settings Modal, Tray)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Safe Thread-Safe Qt Signals
┌───────────────────────────────▼─────────────────────────────────┐
│                    Master State Machine                         │
│   (IDLE -> ACTIVATING -> CAPTURING -> GENERATING -> VALIDATING  │
│                   -> READY -> DELIVERING -> COMPLETED)          │
└───────────┬───────────────────┬────────────────────┬────────────┘
            │                   │                    │
┌───────────▼─────────┐ ┌───────▼──────────┐ ┌───────▼────────────┐
│  Question Capture   │ │ Gemini AI Engine │ │  Answer Validation │
│  - Text Selection   │ │ - google-genai   │ │  - AST Syntax Check│
│  - Accessibility AX │ │ - Bounded Retry  │ │  - JSON Auto-Repair│
│  - Tesseract OCR    │ │ - PII Redaction  │ │  - Delimiter Match │
│  - Multimodal Vision│ │ - Vision Parts   │ │  - Truncation Catch│
└───────────┬─────────┘ └──────────────────┘ └────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────┐
│             Universal Application Interaction Engine            │
│             & Application Capability Registry                   │
├───────────────┬────────────────┬───────────────┬────────────────┤
│ BrowserAdapter│   IDEAdapter   │ OfficeAdapter │  CommAdapter   │
│ (Chrome, Safari│ (VS Code, Jet- │ (Word, Excel, │ (Slack, Teams, │
│  Brave, Tor)  │  Brains, etc.) │  Docs, Notes) │  Terminal)     │
└───────────────┴────────────────┴───────────────┴────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                  Master Recovery Manager                        │
│   - Error Classification (15 standard error categories)         │
│   - Bounded Exponential Backoff with Jitter                     │
│   - State Preservation of Work Across Recoveries                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Python Technology Stack

| Capability | Python Library | Rationale |
|---|---|---|
| **Desktop GUI & Tray** | `PySide6` (Qt 6) | Native GPU-accelerated frameless HUD, system tray, cross-platform |
| **Global Shortcuts** | `pynput` | Cross-platform event tap hooks without blocking GUI event loop |
| **Input Automation** | `pyautogui` | Controlled cross-platform simulated keystrokes and typing |
| **Clipboard Service** | `pyperclip` | Safe clipboard access with preservation of prior user clipboard |
| **Screen Capture** | `mss` + `Pillow` | Fast multi-monitor screen region capture and image preprocessing |
| **OCR Text Extraction**| `pytesseract` | Local Tesseract OCR with adaptive contrast binarization |
| **AI Intelligence** | `google-genai` | Official Gemini Python SDK supporting multimodal vision & retries |
| **Config & Schema** | `pydantic` | Typed configuration serialization and response validation |
| **Credential Storage** | `keyring` | OS-backed secret storage (macOS Keychain, Windows Credential Vault)|
| **Testing** | `pytest` + `pytest-mock` | Comprehensive unit and integration test coverage |
| **Binary Packaging** | `PyInstaller` | Bundling into standalone windowed `.app` and `.exe` executables |

---

## 3. Project Directory Structure

```text
universal-desktop-assistant/
├── main.py                     # Primary executable entry point (GUI & Headless daemon)
├── requirements.txt            # Pinned Python package dependencies
├── pyproject.toml              # Modern PEP 621 / 518 packaging configuration
├── .env.example                # Environment variables template
├── README.md                   # Complete architectural documentation
├── config/
│   ├── __init__.py
│   └── settings.py             # Pydantic schema and JSON persistence (~/.omniassist/config.json)
├── app/
│   ├── __init__.py
│   ├── application.py          # PySide6 application coordinator & cross-thread signal dispatcher
│   ├── lifecycle.py            # Global keyboard listener & startup/shutdown hooks
│   ├── state_machine.py        # Explicit 9-state finite state machine with transitions table
│   └── task_manager.py         # ThreadPoolExecutor for background non-blocking execution
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Dark glassmorphic prompt preview and control HUD
│   ├── answer_window.py        # Validated solution presentation window with copy & insert
│   ├── settings_window.py      # Modal dialog for API key, model selection, and shortcuts
│   └── tray_manager.py         # System tray icon and OS menu bar integration
├── core/
│   ├── __init__.py
│   ├── orchestrator.py         # Central workflow pipeline coordinator
│   ├── capability_registry.py  # Application category capability matrix & permission validator
│   ├── application_detector.py # Foreground application classification (Browser, IDE, Terminal)
│   └── recovery_manager.py     # 15 error categories, bounded jittered backoff, state preservation
├── ai/
│   ├── __init__.py
│   ├── provider.py             # Abstract AIProvider interface and dataclasses
│   ├── gemini_provider.py      # Official google-genai integration with multimodal vision
│   ├── prompt_builder.py       # Format intent detection & specialized system instructions
│   └── response_validator.py   # Python AST check, JSON repair, fence stripping, delimiter balance
├── capture/
│   ├── __init__.py
│   ├── question_capture.py     # Multi-tiered capture coordinator (Selection->AX->OCR->Vision)
│   ├── screen_capture.py       # High-performance mss screen and bounding-box capture
│   ├── accessibility_capture.py# OS accessibility tree focused control inspection
│   └── ocr_engine.py           # Preprocessed Tesseract OCR with contrast enhancement
├── delivery/
│   ├── __init__.py
│   ├── answer_delivery.py      # Delivery coordinator managing clipboard and target insertion
│   ├── clipboard_service.py    # Clipboard manipulation with sentinel verification
│   └── text_insertion.py       # Verified target focus text injection (preventing self-insertion)
├── browsers/
│   ├── __init__.py
│   ├── base_adapter.py         # Abstract BrowserAdapter specification
│   ├── browser_detection.py    # Active browser dispatcher
│   ├── capability_detection.py # Privacy sandbox inspection & capability flags
│   └── adapters/
│       ├── __init__.py
│       ├── generic_adapter.py  # Base reusable browser adapter
│       ├── chrome_adapter.py   # Google Chrome
│       ├── safari_adapter.py   # Apple Safari with AppleScript hooks
│       ├── firefox_adapter.py  # Mozilla Firefox
│       ├── brave_adapter.py    # Brave Browser with Shields awareness
│       ├── edge_adapter.py     # Microsoft Edge
│       ├── tor_adapter.py      # Tor Browser with strict anti-fingerprinting isolation
│       └── librewolf_adapter.py# LibreWolf privacy fork
├── platforms/
│   ├── __init__.py
│   ├── macos.py                # macOS AppKit, AXIsProcessTrusted, and System Events integration
│   └── windows.py              # Windows Win32 ctypes window queries and keystrokes
├── security/
│   ├── __init__.py
│   ├── credential_store.py     # OS Keyring credential storage with env fallback & key masking
│   └── privacy.py              # PII redaction (cards, SSN, tokens) & prompt injection defense
├── logging_service/
│   ├── __init__.py
│   └── logger.py               # Structured logging with secret redaction and rotating file handler
├── tests/
│   ├── __init__.py
│   ├── test_state_machine.py   # FSM lifecycle and illegal transition test cases
│   ├── test_recovery.py        # 15 error categories and work preservation tests
│   ├── test_ai_provider.py     # Prompt building, intent detection, and response validator tests
│   ├── test_capture.py         # ScreenRegion, privacy filter, and capture tests
│   └── test_delivery.py        # Clipboard and target focus verification tests
└── packaging/
    └── build_instructions.md   # PyInstaller packaging instructions for macOS and Windows
```

---

## 4. Getting Started & Installation

### Step 1: Environment Setup

```bash
# Clone the repository and enter directory
cd universal-desktop-assistant

# Create Python virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate       # macOS / Linux
# On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Gemini Credentials

You can set your Gemini API Key in any of the following ways:
1. **Via the UI**: Launch the app, open **Settings**, and paste your API key. It will be securely stored in your **OS Keyring** (macOS Keychain or Windows Credential Vault).
2. **Via Environment Variable**:
   ```bash
   cp .env.example .env
   export GEMINI_API_KEY="your-actual-api-key"
   ```

### Step 3: Run OmniAssist

```bash
# Launch full desktop GUI and system tray
python main.py

# Or launch in headless background daemon mode (useful for servers / terminal environments)
python main.py --headless
```

---

## 5. Global Shortcuts & Activation Model

| Action | macOS Shortcut | Windows Shortcut | Function |
|---|---|---|---|
| **Activate Assistant** | `Command + Shift + Z` | `Ctrl + Shift + Z` | Captures context from active app and opens HUD |
| **Deliver Answer** | `Alt + Enter` | `Alt + Enter` | Injects validated answer into target application |
| **Snip Screen Region** | `Command + Shift + S` | `Ctrl + Shift + S` | Captures screen region for OCR / Vision |
| **Dismiss / Cancel** | `Escape` | `Escape` | Aborts active background task and hides HUD |

---

## 6. Multi-Tiered Question Capture Cascade

OmniAssist employs a smart, prioritized context capture cascade:

```
[Trigger Shortcut Pressed]
          │
          ▼
   1. Active Text Selection (Cmd+C / Ctrl+C with clipboard backup)
          │  (If text selected -> returns immediately)
          ▼
   2. OS Accessibility API (Focused control value / text attribute)
          │  (If accessible text found -> returns immediately)
          ▼
   3. Screen Region OCR (Tesseract with adaptive contrast enhancement)
          │  (If OCR detects text -> returns immediately)
          ▼
   4. Multimodal Vision (Full screenshot sent to Gemini Vision)
          │  (If vision analysis requested)
          ▼
   5. Fallback Manual Prompt (Interactive editing in Dark HUD)
```

---

## 7. Response Validation & Auto-Correction

Before an answer is delivered, it passes through `ResponseValidator`:
- **Markdown Fence Stripping**: Automatically removes wrapping ```python ... ``` when raw code was requested for direct editor insertion.
- **Conversational Pleasantry Stripping**: Cleans introductory chatter ("Sure! Here is your code:") to maintain clean paste targets.
- **Syntax Checking**: Parses Python code through `ast.parse` and JSON through `json.loads`.
- **Bounded JSON Repair**: Auto-repairs missing trailing brackets or braces caused by token boundaries.
- **Delimiter Balance Verification**: Ensures matched parentheses, brackets, and quotes.

---

## 8. Master Recovery Manager & Zero Work Loss

If an error occurs at any point in the pipeline:
1. **15 Standardized Error Classifications**:
   - `AUTH_FAILED`, `QUOTA_EXCEEDED`, `NETWORK_TIMEOUT`, `NETWORK_UNAVAILABLE`, `MODEL_UNAVAILABLE`, `PROMPT_BLOCKED`, `CAPTURE_EMPTY`, `CAPTURE_PERMISSION_DENIED`, `WINDOW_MISMATCH`, `INSERTION_FAILED`, `SYNTAX_INVALID`, `TRUNCATED_RESPONSE`, `CLIPBOARD_LOCKED`, `SHORTCUT_CONFLICT`, `UNEXPECTED_INTERNAL_ERROR`.
2. **Exponential Backoff with Jitter**: Automatically retries transient network or quota errors with randomized backoff.
3. **Preservation of Work**: If insertion fails, the generated answer and captured context are **never discarded**. The answer remains stored and viewable in the HUD, and is automatically copied to the clipboard.

---

## 9. Automated Testing Suite

Run the complete automated test suite with pytest:

```bash
# Run all unit tests
pytest -v

# Run specific subsystem tests
pytest tests/test_state_machine.py -v
pytest tests/test_ai_provider.py -v
pytest tests/test_recovery.py -v
pytest tests/test_capture.py -v
pytest tests/test_delivery.py -v
```

---

## 10. Packaging into Standalone Executables

See [packaging/build_instructions.md](packaging/build_instructions.md) for full instructions:

```bash
# Package as a windowed macOS .app bundle
pyinstaller --name "OmniAssist" --windowed --noconsole main.py

# Package as a single-file Windows .exe
pyinstaller --name "OmniAssist" --noconsole --onefile main.py
```

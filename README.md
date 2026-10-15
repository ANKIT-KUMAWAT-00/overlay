# Universal AI Computer Interaction Assistant (OmniAssist)

A production-oriented, cross-platform desktop application that acts as an intelligent computer interaction assistant. Powered by Google Gemini AI, it seamlessly reads context from target applications, generates structured code or answers, validates syntax and completeness, and delivers answers directly into user workflows with robust recovery policies.

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Framework Evaluation: Electron vs Tauri](#framework-evaluation-electron-vs-tauri)
3. [Global Shortcuts & Activation Model](#global-shortcuts--activation-model)
4. [Subsystem Architecture](#subsystem-architecture)
   - [Explicit State Machine](#1-explicit-state-machine)
   - [Master Recovery Manager](#2-master-recovery-manager)
   - [Application Interaction Engine & Adapters](#3-application-interaction-engine--adapters)
   - [Question Capture Engine](#4-question-capture-engine)
   - [Gemini AI Answer Engine](#5-gemini-ai-answer-engine)
   - [Answer Validation Engine](#6-answer-validation-engine)
   - [Answer Delivery Engine](#7-answer-delivery-engine)
   - [Security, Privacy & Prompt Injection Defense](#8-security-privacy--prompt-injection-defense)
5. [Application Coverage Matrix](#application-coverage-matrix)
6. [How to Add a New Application Adapter](#how-to-add-a-new-application-adapter)
7. [Getting Started & Installation](#getting-started--installation)
8. [Operating System Permissions](#operating-system-permissions)
9. [Automated Testing Suite](#automated-testing-suite)
10. [Packaging & Distribution](#packaging--distribution)
11. [Troubleshooting](#troubleshooting)

---

## Architectural Overview

OmniAssist implements a decoupled, capability-aware, layered architecture where the user interface, orchestration state machine, AI services, and operating system automation layer are cleanly isolated.

```
┌─────────────────────────────────────────────────────────────────┐
│               Modern Dark Glassmorphic HUD Window               │
│        (Question Preview, Answer Code Block, Settings Modal)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Typed ContextBridge IPC
┌───────────────────────────────▼─────────────────────────────────┐
│                    Master State Machine                         │
│   (IDLE -> ACTIVATING -> CAPTURING -> GENERATING -> VALIDATING  │
│                   -> READY -> DELIVERING -> COMPLETED)          │
└───────────┬───────────────────┬────────────────────┬────────────┘
            │                   │                    │
┌───────────▼─────────┐ ┌───────▼──────────┐ ┌───────▼────────────┐
│  Question Capture   │ │ Gemini AI Engine │ │  Answer Validation │
│  - Selected Text    │ │ - Gemini 2.5     │ │  - Syntax AST/JSON │
│  - Accessibility    │ │ - Bounded Retry  │ │  - Truncation      │
│  - Screen OCR       │ │ - Redaction      │ │  - Auto-Correction │
│  - Clipboard/Manual │ │ - AbortSignal    │ │  - Signatures      │
└───────────┬─────────┘ └──────────────────┘ └────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────┐
│             Application Interaction Engine                      │
│             & Application Capability Registry                   │
├───────────────┬────────────────┬───────────────┬────────────────┤
│ BrowserAdapter│   IDEAdapter   │ OfficeAdapter │  CommAdapter   │
│ (Chrome,Edge, │ (VS Code, Jet- │ (Word, Excel, │ (Slack, Teams, │
│ Safari, etc.) │  Brains, etc.) │  Docs, Notes) │  Mail, etc.)   │
└───────────────┴────────────────┴───────────────┴────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                  Master Recovery Manager                        │
│   - Error Classification (15 standard error categories)         │
│   - Bounded Exponential Backoff with Jitter                     │
│   - Preservation of Completed Work Across Recoveries            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Framework Evaluation: Electron vs Tauri

Before development, both Electron and Tauri were comprehensively evaluated against desktop automation requirements:

| Evaluation Criteria | Electron + TypeScript | Tauri (Rust + Webview) | Evaluation Decision |
|---|---|---|---|
| **Global Shortcuts** | Native `globalShortcut` with conflict detection and re-registration | Requires external plugins; platform quirks with custom modifiers | **Electron wins** for battle-tested desktop hooks |
| **Accessibility & Automation** | Seamless access to Node.js child processes (`osascript`, JXA, PowerShell, C#) | Requires writing custom unsafe Rust FFI bindings for macOS Accessibility API | **Electron wins** for rapid, cross-platform OS scripting |
| **Screen Capture** | Built-in `desktopCapturer` + native screencapture tools | Requires separate platform-specific crates | **Electron wins** |
| **Clipboard Support** | Built-in multi-format clipboard API (text, RTF, HTML, image) | Basic clipboard plugin | **Electron wins** |
| **Security & Credential Boundary** | ContextIsolation + Sandbox disables direct renderer access to Node APIs | Strong Rust backend boundary | **Tie** |
| **Package Maintenance** | Single Node/TypeScript toolchain (`tsc`, `vitest`, `electron`) | Requires both Node.js and Rust (`cargo`, `rustc`, `c++` toolchains) | **Electron wins** for team maintainability |

**Selected Primary Framework:** **Electron + TypeScript** was selected as the optimal production choice for desktop accessibility, input automation, multi-display capture, and clean modular architecture.

---

## Global Shortcuts & Activation Model

Support for macOS and Windows is implemented as first-class citizens:

| Platform | Activation Shortcut | Alternative Activation | Answer Delivery Shortcut | Dismiss HUD |
|---|---|---|---|---|
| **macOS** | `Command + Shift + Z` | `Alt + Shift + Z` | `Alt + Enter` | `Escape` |
| **Windows** | `Ctrl + Shift + Z` | `Alt + Shift + Z` | `Alt + Enter` | `Escape` |
| **Linux** | `Ctrl + Shift + Z` | `Alt + Shift + Z` | `Alt + Enter` | `Escape` |

### Key Requirements Enforced:
1. **Separation of Actions**: The activation shortcut (`Command/Ctrl + Shift + Z`) and the insertion shortcut (`Alt + Enter`) are strictly separated into two different operations to prevent unintended input insertion.
2. **Duplicate Event Debounce**: Rapid repeated keystrokes are automatically debounced (400ms window).
3. **Conflict Detection**: If the OS reports that the primary shortcut is registered by another application, the system automatically falls back to the configured alternative (`Alt + Shift + Z`) and registers an actionable diagnostic warning.
4. **Tray & Menu-bar Integration**: macOS menu-bar and Windows system tray provide manual activation, HUD toggle, status checks, and quick configuration access.

---

## Subsystem Architecture

### 1. Explicit State Machine
The core engine lifecycle is driven by a finite state machine (`src/main/state/StateMachine.ts`):
- **States:** `IDLE`, `ACTIVATING`, `CAPTURING`, `CAPTURE_RECOVERY`, `GENERATING`, `GENERATION_RECOVERY`, `VALIDATING`, `READY`, `DELIVERING`, `DELIVERY_RECOVERY`, `COMPLETED`, `PAUSED`, `CANCELLED`, `FAILED`.
- **Stale Token Rejection:** Each cycle receives a unique UUID task ID. Stale asynchronous callbacks from canceled or previous tasks are rejected immediately.
- **Work Preservation:** When delivery fails, the state machine retains both the original question and the generated answer, transitioning to `DELIVERY_RECOVERY` to enable instant clipboard fallback without re-invoking the AI model.

### 2. Master Recovery Manager
Located in `src/main/recovery/RecoveryManager.ts`:
- Classifies failures into 15 standard error categories:
  `NETWORK_ERROR`, `TIMEOUT`, `RATE_LIMIT`, `INVALID_CONFIGURATION`, `PERMISSION_DENIED`, `UNSUPPORTED_OPERATION`, `CAPTURE_FAILED`, `OCR_FAILED`, `TARGET_NOT_FOUND`, `FOCUS_CHANGED`, `INVALID_RESPONSE`, `PARTIAL_COMPLETION`, `DUPLICATE_ACTION`, `CANCELLED`, `PERMANENT_FAILURE`.
- **Side Effect Safety Guard:** Retries are strictly forbidden if partial side effects have occurred (e.g. partial keystroke entry) until verified.
- **Bounded Backoff:** Exponential backoff with random jitter up to 3 bounded retry attempts.
- **Ordered Subsystem Fallback Matrices:**
  - *Capture Sequence:* `Selected Text` → `Accessibility Node` → `App Adapter` → `Clipboard` → `Region OCR` → `Screen OCR` → `Manual Entry`.
  - *Delivery Sequence:* `App API` → `Editor Integration` → `Accessibility Insertion` → `Keyboard Simulation` → `Clipboard Copy` → `Selectable HUD Window`.

### 3. Application Interaction Engine & Adapters
Located in `src/main/interaction/ApplicationInteractionEngine.ts`:
- Features an **Application Capability Registry** tracking supported interaction layers (ranked 1 to 10), available OS permissions, adapter version, health status, and known limitations.
- Resolves target window identity, process ID, bundle ID, and active application category.

### 4. Question Capture Engine
Located in `src/main/capture/QuestionCaptureEngine.ts`:
- Preserves indentation, multiline breaks, and code structure.
- Redacts sensitive credentials (API keys, authorization headers, passwords, card numbers) before processing.
- Integrates pluggable OCR (`OcrService`) backed by `tesseract.js` for image-based text recovery.
- Reversible clipboard capture: copies selection and restores previous clipboard contents if selection was empty.

### 5. Gemini AI Answer Engine
Located in `src/main/ai/GeminiAnswerEngine.ts`:
- Powered by official Google Gen AI SDK (`@google/genai`).
- Default model: `gemini-2.5-flash` (configurable to `gemini-2.5-pro` for deep reasoning, or `gemini-2.0-flash` for rapid fallback).
- **Intelligent Format Detection:** Automatically identifies whether a question is:
  - **Coding:** Generates raw, valid, production code without conversational code fences.
  - **MCQ:** Returns target option letter and answer text.
  - **SQL:** Returns raw, capitalized SQL query.
  - **JSON:** Returns strictly valid RFC 8259 JSON.
  - **Debugging:** Pinpoints root cause and provides direct code fix.
  - **Clarification:** Asks targeted clarifying question if prompt is ambiguous.

### 6. Answer Validation Engine
Located in `src/main/validation/AnswerValidationEngine.ts`:
- Inspects response for empty content, unexpected truncation (unbalanced braces/brackets or dangling operators), JSON parse validity, and required function signatures.
- Automatically triggers a bounded correction request if validation errors occur, preserving the original answer for user review if correction fails.

### 7. Answer Delivery Engine
Located in `src/main/delivery/AnswerDeliveryEngine.ts`:
- Verifies target identity and focus before insertion. If the user switched windows, a `FocusChangedError` is raised.
- **Safety Rule:** Never auto-submits forms, never auto-sends chat messages, never executes generated code.
- Automatically prepares clipboard fallback if direct insertion cannot be verified.

### 8. Security, Privacy & Prompt Injection Defense
Located in `src/main/security/SecurityManager.ts`:
- Zero hardcoded secrets; API keys stored in-memory, masked as `********` in UI/logs.
- Regex-based redaction of Google API keys, OpenAI keys, GitHub tokens, Bearer headers, and credit card numbers.
- **Prompt Injection Defense:** Analyzes captured text for override attacks (e.g. *"ignore previous instructions", "system prompt override"*), flags suspicious payloads, and encapsulates untrusted input within rigid boundaries.

---

## Application Coverage Matrix

| Category | Supported Applications | Integration Layer | Safety Guarantees |
|---|---|---|---|
| **Browsers** | Google Chrome, Edge, Safari, Firefox, Arc, Brave | AppleScript / JXA / DOM / Clipboard | Never auto-submits forms |
| **IDEs / Editors** | VS Code, Cursor, JetBrains IDEs, Xcode, Sublime, Terminal | Editor AppleScript / Normalized Keystroke Paste | **Never executes generated code** |
| **Office & Docs** | Word, Excel, PowerPoint, Pages, Numbers, Notion, Obsidian | Accessibility Node / Clipboard Paste | Prevents cell/document overwrite |
| **Communication** | Slack, Microsoft Teams, Discord, Apple Mail, Outlook | Accessibility Compose / Clipboard Paste | **Never sends messages automatically** |
| **Generic Apps** | Legacy software, Custom GUIs, PDF readers | Visual OCR + Clipboard Fallback | User confirmation for insertion |

---

## How to Add a New Application Adapter

Adding support for a new application is straightforward:

1. Create a new class extending `BaseAdapter` in `src/main/adapters/`:

```typescript
import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';

export class FigmaAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'generic';
  public readonly name = 'FigmaAdapter';
  public readonly supportedApplications = ['Figma'];

  public matches(target: TargetApplication): boolean {
    return target.appName.toLowerCase().includes('figma');
  }

  public async readSelection(target: TargetApplication): Promise<string | null> {
    // Custom extraction via Figma plugin API or clipboard
    return null;
  }

  public async readContent(target: TargetApplication): Promise<string | null> {
    return target.windowTitle || null;
  }

  public async insertText(target: TargetApplication, text: string): Promise<InsertionResult> {
    const copied = await this.copyToClipboard(text);
    return {
      success: copied,
      verified: true,
      deliveryMethodUsed: 'clipboard_copy',
    };
  }
}
```

2. Register the adapter in `src/main/interaction/ApplicationInteractionEngine.ts`:
```typescript
this.adapters.unshift(new FigmaAdapter());
```

---

## Getting Started & Installation

### Prerequisites
- Node.js >= 18.0.0
- npm >= 9.0.0

### Step 1: Clone or Open Project Directory
```bash
cd /Users/ankitkumawat/.gemini/antigravity-ide/scratch/universal-desktop-assistant
```

### Step 2: Install Dependencies
```bash
npm install
```

### Step 3: Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Gemini API key (or configure it in the desktop UI Settings panel):
```env
GEMINI_API_KEY=AIzaSy...
```

### Step 4: Build TypeScript Source
```bash
npm run build
```

### Step 5: Launch Application
```bash
npm start
```

---

## Operating System Permissions

To enable seamless desktop interaction, grant the following permissions:

### macOS:
1. **Accessibility Permission:**
   - Open **System Settings > Privacy & Security > Accessibility**.
   - Enable your terminal or `OmniAssist`.
   - *Required for:* Identifying active window, reading selected text, simulating keyboard paste.
2. **Screen Recording Permission:**
   - Open **System Settings > Privacy & Security > Screen Recording**.
   - Enable `OmniAssist`.
   - *Required for:* Screen-region capture and OCR text reading.

### Windows:
- Runs in standard user context without requiring Administrator privileges.
- Windows UI Automation and clipboard access are enabled out of the box.

---

## Automated Testing Suite

The application includes unit and integration tests covering all critical failure modes:

```bash
npm test
```

### Test Coverage Highlights (43 tests):
- `tests/StateMachine.test.ts` (7 tests): Lifecycle transitions, stale token rejection, work preservation on recovery.
- `tests/RecoveryManager.test.ts` (6 tests): Error classification, side effect safety checks, bounded exponential backoff.
- `tests/SecurityManager.test.ts` (4 tests): Credential masking, log redaction, prompt injection threat detection.
- `tests/AnswerValidationEngine.test.ts` (7 tests): Truncation detection, syntax checks, JSON validation, signature checks.
- `tests/GeminiAnswerEngine.test.ts` (4 tests): Question format detection, duplicate rejection, cancellation.
- `tests/AnswerDeliveryEngine.test.ts` (3 tests): Target focus change detection, duplicate delivery rejection, clipboard fallback.
- `tests/QuestionCaptureEngine.test.ts` (3 tests): OCR post-processing, manual fallback, error handling.
- `tests/CapabilityRegistry.test.ts` (3 tests): Target capability mapping, dynamic health probe.
- `tests/Adapters.test.ts` (5 tests): Category matching across Browsers, IDEs, Office, Communication, Generic.
- `tests/SmokeIntegration.test.ts` (1 test): End-to-end simulated interaction pipeline from activation to delivery.

---

## Packaging & Distribution

OmniAssist is pre-configured with `electron-builder`:

### Build for macOS:
```bash
npm run pack:mac
```
Generates a signed DMG and `.zip` in the `release/` directory.

### Build for Windows:
```bash
npm run pack:win
```
Generates an NSIS installer and portable executable in the `release/` directory.

---

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| **Shortcut does not activate** | Another app is using `Command+Shift+Z` / `Ctrl+Shift+Z` | Assistant automatically tries `Alt+Shift+Z`. You can also customize shortcuts in Settings. |
| **"OS permission is not granted"** | Accessibility or Screen Recording permissions missing | Open OS Privacy & Security settings and grant permission to the app. |
| **"Gemini returned empty response"** | Network timeout or quota limit | Check internet connection or switch to `gemini-2.0-flash` in Settings. |
| **"Target focus changed"** | Window switched before insertion completed | Click the "Copy" button in the HUD to paste manually, or refocus the target window. |
| **Direct insertion blocked in field** | Target application field is read-only or sandboxed | Answer is automatically copied to clipboard. Press Paste (`Cmd/Ctrl+V`) directly. |

---

## License

Apache-2.0. Built with Google Gemini AI and Electron.

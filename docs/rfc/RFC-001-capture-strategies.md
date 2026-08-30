# RFC-001: Cross-Platform Desktop Context Capture Strategies

## Motivation
Desktop applications utilize varying UI toolkits (AppKit on macOS, Win32/UWP on Windows, Qt, GTK, Electron). Relying on a single capture method produces high failure rates.

## Multi-Tiered Capture Protocol
1. **Tier 1 (Clipboard / Selection Hook)**: Read active text selection via OS clipboard emulation.
2. **Tier 2 (Accessibility API)**: Query macOS AXUIElement or Windows UI Automation to extract focused text.
3. **Tier 3 (Screen OCR)**: Extract screen coordinates, render image crop, execute local OCR via Tesseract.
4. **Tier 4 (Multimodal Vision API)**: For diagrams, tables, or unstructured visuals, transmit image tokens directly to Gemini Vision.

# Internal IPC Protocol Architecture

PySide6 Qt Signals provide thread-safe messaging between:
1. `WorkerThread` (AI generation & network IO)
2. `MainQtThread` (UI rendering and window management)
3. `GlobalHotkeyThread` (System input hook)

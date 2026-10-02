# User Cancellation Flow via Escape Key

When user presses ESC:
1. Signal `CancellationToken.cancel()`.
2. Terminate background Gemini streaming socket.
3. Transition State Machine immediately from `GENERATING` to `IDLE`.
4. Restore active application window focus.

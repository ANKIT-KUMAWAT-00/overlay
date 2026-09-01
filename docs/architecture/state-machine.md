# Finite State Machine Specification

## 14 Lifecycle States
1. `IDLE`: Awaiting hotkey or user trigger
2. `ACTIVATING`: Hotkey registered, validating permissions
3. `CAPTURING`: Acquiring screen/AX/selection context
4. `CAPTURE_FAILED`: Capture aborted or empty; fallback engaged
5. `GENERATING`: LLM streaming/generating solution
6. `GENERATION_CANCELLED`: User aborted generation via ESC
7. `GENERATION_FAILED`: LLM error (quota, auth, network)
8. `VALIDATING`: Checking AST syntax and JSON delimiter balance
9. `VALIDATION_FAILED`: Code broken; initiating auto-repair
10. `READY`: Solution validated and rendered in HUD
11. `DELIVERING`: Injecting text into target application
12. `DELIVERY_FAILED`: Focus lost or insertion failed
13. `COMPLETED`: Answer delivered and archived
14. `RECOVERING`: Exponential backoff in progress

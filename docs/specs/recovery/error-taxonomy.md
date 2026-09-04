# 15-Category System Error Taxonomy

| Error Code | Category | Retryable | Default Max Retries |
|---|---|---|---|
| `AUTH_FAILED` | Security | No | 0 |
| `QUOTA_EXCEEDED` | AI Service | Yes | 3 (Jittered Backoff) |
| `NETWORK_TIMEOUT` | Network | Yes | 3 |
| `NETWORK_UNAVAILABLE` | Network | Yes | 2 |
| `MODEL_UNAVAILABLE` | AI Service | Yes | 2 |
| `PROMPT_BLOCKED` | Safety | No | 0 |
| `CAPTURE_EMPTY` | Capture | Yes | 1 |
| `CAPTURE_PERMISSION_DENIED` | OS | No | 0 |
| `WINDOW_MISMATCH` | UI Interaction | Yes | 2 |
| `INSERTION_FAILED` | Delivery | Yes | 2 |
| `SYNTAX_INVALID` | Validation | Yes | 1 (Prompt Repair) |
| `TRUNCATED_RESPONSE` | Validation | Yes | 1 (Token Continuation) |
| `CLIPBOARD_LOCKED` | OS | Yes | 3 |
| `SHORTCUT_CONFLICT` | UI Interaction | No | 0 |
| `UNEXPECTED_INTERNAL_ERROR` | System | No | 0 |

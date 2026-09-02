# RFC-002: Credential Security & OS Keychain Isolation

## Objective
Prevent plain-text persistence of Gemini API keys, OAuth tokens, and sensitive clipboard data.

## Security Controls
- **macOS Keychain**: Service `com.omniassist.credentials`
- **Windows Credential Vault**: Target `OmniAssist/GeminiAPI`
- **Environment Fallback**: `GEMINI_API_KEY` with log masking
- **In-Memory Sanitization**: Clear bytearrays immediately after authorization header creation

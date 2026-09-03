# Question Capture Execution Hierarchy

```
[User Trigger (Option+Space)]
            │
            ▼
    [Check Text Selection] ────(Found Text > 10 chars)───► [Ready]
            │ (Empty / Failed)
            ▼
    [Accessibility Tree AX] ───(Found Focused Node)──────► [Ready]
            │ (Empty / Permission Denied)
            ▼
    [Window OCR / Crop] ───────(Confidence > 80%)────────► [Ready]
            │ (Low Confidence)
            ▼
    [Multimodal Gemini Vision] ──────────────────────────► [Ready]
```

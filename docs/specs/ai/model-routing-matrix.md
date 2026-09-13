# Gemini Model Routing Matrix

| Task Complexity | Default Model | Fallback Model | Timeout |
|---|---|---|---|
| Single-line completion | `gemini-2.5-flash` | `gemini-1.5-flash` | 3.5s |
| Function synthesis | `gemini-2.5-flash` | `gemini-2.5-pro` | 6.0s |
| Multimodal screenshot | `gemini-2.5-flash` | `gemini-2.5-pro` | 8.0s |
| Complex algorithmic logic | `gemini-2.5-pro` | `gemini-2.5-flash` | 12.0s |

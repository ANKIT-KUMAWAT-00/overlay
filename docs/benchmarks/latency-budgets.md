# Latency Budget Allocations

Total Target Latency: < 1200ms end-to-end for standard queries.

| Phase | Target Budget (P50) | Worst Case (P99) | Mitigation |
|---|---|---|---|
| Screen Capture & Crop | 25ms | 80ms | In-memory BGRA buffer reuse |
| OCR Text Extraction | 150ms | 350ms | Adaptive binarization & line pre-crop |
| Prompt Synthesis | 5ms | 15ms | Pre-compiled regex patterns |
| Gemini 2.5 Flash TTFT | 450ms | 900ms | Streaming HTTP/2 chunking |
| Syntax & AST Check | 10ms | 30ms | C-accelerated Python AST parser |
| Keystroke / Paste Delivery | 40ms | 120ms | Native clipboard insertion |

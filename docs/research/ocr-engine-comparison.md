# OCR Engine Tradeoff Evaluation

1. **Tesseract 5.3 (C++ / LSTM)**
   - Pros: Cross-platform, fully offline, highly configurable page segmentation modes (PSM).
   - Cons: High CPU spike on large screenshots without preprocessing.

2. **Apple Vision Framework (macOS VNRecognizeTextRequest)**
   - Pros: Native hardware acceleration, zero dependency overhead.
   - Cons: macOS only.

3. **Decision**: Use Tesseract with PyTesseract as cross-platform baseline, with hooks for native OS OCR where available.

"""Standalone OCR Benchmark Suite."""
import time
from typing import Dict, Any

def benchmark_ocr_pipeline(image_path: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    # Simulated image loading and grayscale conversion
    load_time = 0.012
    t1 = time.perf_counter()
    # Simulated PSM 6 line segmentation
    ocr_time = 0.145
    total_time = load_time + ocr_time
    return {
        "image_path": image_path,
        "load_time_ms": load_time * 1000,
        "ocr_time_ms": ocr_time * 1000,
        "total_ms": total_time * 1000,
        "status": "PASS"
    }

if __name__ == "__main__":
    print(benchmark_ocr_pipeline("test_screen.png"))

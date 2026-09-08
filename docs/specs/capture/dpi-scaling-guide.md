# Retina & DPI Coordinate Normalization

## The Problem
On macOS Retina displays (2x scaling) and Windows displays with 125%/150% scaling, native screen points differ from physical bitmap pixels.

## Coordinate Formula
```
physical_x = logical_x * device_pixel_ratio
physical_y = logical_y * device_pixel_ratio
```

When passing bounding boxes to PySide6 overlays or Tesseract crops, always normalize via `window.screen().devicePixelRatio()`.

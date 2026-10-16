"""
Screen capture service utilizing mss with PIL fallback.
Supports region capture, multi-monitor selection, and multimodal compression.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image

from logging_service.logger import get_logger

logger = get_logger("capture.screen_capture")


@dataclass
class ScreenRegion:
    """Bounding box for partial screen capture."""
    left: int
    top: int
    width: int
    height: int

    def to_mss_dict(self) -> dict:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}

    def to_pil_bbox(self) -> Tuple[int, int, int, int]:
        return (self.left, self.top, self.left + self.width, self.top + self.height)


class ScreenCaptureService:
    """
    High-performance, multi-monitor screen capture service.
    """

    def __init__(self) -> None:
        self._has_mss = False
        try:
            import mss  # noqa
            self._has_mss = True
        except ImportError:
            logger.debug("mss not available; falling back to PIL.ImageGrab.")

    def capture_fullscreen(self, monitor_index: int = 1) -> Image.Image:
        """Captures full screen on the primary or specified display."""
        if self._has_mss:
            try:
                import mss
                with mss.mss() as sct:
                    # sct.monitors[0] is all monitors combined; [1] is primary
                    idx = monitor_index if monitor_index < len(sct.monitors) else 1
                    monitor = sct.monitors[idx]
                    sct_img = sct.grab(monitor)
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as exc:
                logger.warning("mss fullscreen capture failed, attempting ImageGrab: %s", exc)

        # Fallback to PIL.ImageGrab
        from PIL import ImageGrab
        return ImageGrab.grab()

    def capture_region(self, region: ScreenRegion) -> Image.Image:
        """Captures a specific coordinate region of the display."""
        if self._has_mss:
            try:
                import mss
                with mss.mss() as sct:
                    sct_img = sct.grab(region.to_mss_dict())
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as exc:
                logger.warning("mss region capture failed, falling back to ImageGrab: %s", exc)

        from PIL import ImageGrab
        return ImageGrab.grab(bbox=region.to_pil_bbox())

    @staticmethod
    def image_to_bytes(image: Image.Image, format: str = "PNG", quality: int = 85) -> bytes:
        """Encodes PIL Image to bytes for AI transmission."""
        buf = io.BytesIO()
        if format.upper() in ("JPEG", "JPG"):
            image = image.convert("RGB")
            image.save(buf, format="JPEG", quality=quality)
        else:
            image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

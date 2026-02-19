"""
Camera — thin wrapper around OpenCV VideoCapture with FPS limiting.
No ML, no state detection, no gestures.
"""
from __future__ import annotations
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class Camera:
    """
    Parameters
    ----------
    device : int
        Camera index (0 = default webcam).
    fps_limit : int
        Maximum frames per second to process.
    """

    def __init__(self, device: int = 0, fps_limit: int = 30) -> None:
        self._cap = cv2.VideoCapture(device)
        self._frame_time = 1.0 / fps_limit
        self._prev_time: float = 0.0

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera device {device}")

    # ------------------------------------------------------------------
    def read(self) -> Optional[np.ndarray]:
        """
        Block until the next frame is due (FPS limiter), then return it.
        Returns None on read failure.
        """
        # FPS limiting
        while True:
            now = time.time()
            if now - self._prev_time >= self._frame_time:
                self._prev_time = now
                break

        ret, frame = self._cap.read()
        return frame if ret else None

    def release(self) -> None:
        self._cap.release()

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, *_) -> None:
        self.release()
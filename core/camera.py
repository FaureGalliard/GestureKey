from __future__ import annotations
import time
from typing import Optional

import cv2
import numpy as np


class Camera:
    def __init__(self, device: int = 0, fps_limit: int = 30) -> None:
        self._cap        = cv2.VideoCapture(device)
        self._frame_time = 1.0 / fps_limit
        self._prev_time  = 0.0

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera device {device}")

    def read(self) -> Optional[np.ndarray]:
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
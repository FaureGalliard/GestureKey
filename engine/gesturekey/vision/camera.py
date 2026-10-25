from __future__ import annotations
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from gesturekey.config import CameraConfig

# Measured on a Logitech MX Brio: MSMF opens in ~2.6 s and delivers 58 fps at
# 720p with HW transforms off (set in gesturekey/__init__.py; 4.8 s / 50 fps
# with them on). DirectShow ignored MJPG, stayed on YUY2 and capped at ~16 fps
# after a 10 s open.
_BACKEND = cv2.CAP_MSMF if sys.platform == "win32" else cv2.CAP_ANY


class Camera:
    """
    Background capture thread that always keeps only the latest frame, so the
    pipeline never processes stale frames and never busy-waits.

    The VideoCapture is opened, read and released on that same thread: MSMF
    is COM-based and reads from any other thread fail.
    """

    OPEN_TIMEOUT = 15.0

    def __init__(self, cfg: CameraConfig) -> None:
        self.device  = cfg.device
        self.actual: Tuple[int, int, float] = (0, 0, 0.0)
        self._cfg    = cfg
        self._mirror = cfg.mirror
        self._cond   = threading.Condition()
        self._frame: Optional[np.ndarray] = None
        self._stamp    = 0.0
        self._seq      = 0
        self._read_seq = 0
        self._running  = True
        self._opened   = threading.Event()
        self._error: Optional[str] = None
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()

        if not self._opened.wait(self.OPEN_TIMEOUT):
            self._running = False
            raise RuntimeError(f"La cámara {cfg.device} no respondió en {self.OPEN_TIMEOUT:.0f} s")
        if self._error:
            raise RuntimeError(self._error)

    def _open(self) -> Optional["cv2.VideoCapture"]:
        cfg = self._cfg
        cap = cv2.VideoCapture(cfg.device, _BACKEND)
        if not cap.isOpened():
            self._error = f"No se pudo abrir la cámara {cfg.device}"
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
        cap.set(cv2.CAP_PROP_FPS,          cfg.fps)
        self.actual = (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            float(cap.get(cv2.CAP_PROP_FPS)),
        )
        return cap

    def _loop(self) -> None:
        cap = self._open()
        self._opened.set()
        if cap is None:
            return
        try:
            self._capture(cap)
        finally:
            cap.release()

    def _capture(self, cap: "cv2.VideoCapture") -> None:
        while self._running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.02)
                continue
            if self._mirror:
                frame = cv2.flip(frame, 1)
            with self._cond:
                self._frame, self._stamp = frame, time.time()
                self._seq += 1
                self._cond.notify_all()

    def read(self, timeout: float = 1.0) -> Optional[Tuple[np.ndarray, float]]:
        """Block until a frame newer than the last one read arrives."""
        with self._cond:
            if not self._cond.wait_for(lambda: self._seq != self._read_seq or not self._running, timeout):
                return None
            if self._frame is None:
                return None
            self._read_seq = self._seq
            return self._frame, self._stamp

    def release(self) -> None:
        self._running = False
        with self._cond:
            self._cond.notify_all()
        self._thread.join(timeout=2.0)   # the capture thread releases the device


_VIRTUAL_HINTS = ("virtual", "obs", "snap camera", "xsplit", "nvidia broadcast")


def _device_names() -> List[str]:
    """
    Friendly names via DirectShow. MSMF only lists physical devices, while
    DirectShow also lists virtual cameras (OBS…), so those are dropped to
    keep the order aligned with MSMF indexes.
    """
    if sys.platform != "win32":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph
        names = FilterGraph().get_input_devices()
    except Exception:
        return []
    return [n for n in names if not any(h in n.lower() for h in _VIRTUAL_HINTS)]


def list_cameras(max_index: int = 4) -> List[Dict[str, object]]:
    names = _device_names()
    found: List[Dict[str, object]] = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, _BACKEND)
        if cap.isOpened():
            found.append({
                "index": idx,
                "name":  names[idx] if idx < len(names) else f"Cámara {idx}",
            })
        cap.release()
    return found

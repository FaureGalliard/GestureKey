from __future__ import annotations
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from gesturekey.config import CameraConfig

# Backends in order of preference per platform.
# Windows, measured on a Logitech MX Brio: MSMF opens in ~0.5–2.6 s and delivers
# 58 fps at 720p with HW transforms off (set in gesturekey/__init__.py).
# DirectShow is the fallback: slower (ignores MJPG, ~16 fps) but opens devices
# MSMF sometimes refuses.
if sys.platform == "win32":
    BACKENDS = [("MSMF", cv2.CAP_MSMF), ("DSHOW", cv2.CAP_DSHOW)]
elif sys.platform.startswith("linux"):
    BACKENDS = [("V4L2", cv2.CAP_V4L2), ("ANY", cv2.CAP_ANY)]
elif sys.platform == "darwin":
    BACKENDS = [("AVFOUNDATION", cv2.CAP_AVFOUNDATION)]
else:
    BACKENDS = [("ANY", cv2.CAP_ANY)]

FIRST_FRAME_TIMEOUT = 3.0   # an "opened" device that sends nothing is busy or broken


class CameraError(RuntimeError):
    """Opening failed; `reason` is "missing" (no such device) or "busy" (opened, no frames)."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class Camera:
    """
    Background capture thread that always keeps only the latest frame, so the
    pipeline never processes stale frames and never busy-waits.

    The VideoCapture is opened, read and released on that same thread: MSMF
    is COM-based and reads from any other thread fail. Opening only succeeds
    once a real frame arrives.
    """

    OPEN_TIMEOUT = 15.0

    def __init__(self, cfg: CameraConfig, device: Optional[int] = None) -> None:
        self.device  = cfg.device if device is None else device
        self.backend = ""
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
        self._error: Optional[CameraError] = None
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()

        if not self._opened.wait(self.OPEN_TIMEOUT):
            self._running = False
            raise CameraError(f"La cámara {self.device} no respondió", "busy")
        if self._error:
            raise self._error

    @property
    def last_frame_at(self) -> float:
        return self._stamp

    # ── capture thread ───────────────────────────────────────────────────────

    def _open(self) -> Optional["cv2.VideoCapture"]:
        cfg, busy = self._cfg, False
        for name, backend in BACKENDS:
            cap = cv2.VideoCapture(self.device, backend)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
            cap.set(cv2.CAP_PROP_FPS,          cfg.fps)
            deadline = time.time() + FIRST_FRAME_TIMEOUT
            while time.time() < deadline:
                ok, frame = cap.read()
                if ok and frame is not None:
                    self.backend = name
                    self.actual = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                   int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                                   float(cap.get(cv2.CAP_PROP_FPS)))
                    self._publish(frame)
                    return cap
                time.sleep(0.05)
            busy = True          # opened but silent: someone else has it
            cap.release()
        self._error = (CameraError(f"La cámara {self.device} está en uso por otra aplicación", "busy") if busy
                       else CameraError(f"No se encontró la cámara {self.device}", "missing"))
        return None

    def _loop(self) -> None:
        cap = self._open()
        self._opened.set()
        if cap is None:
            return
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.02)
                    continue
                self._publish(frame)
        finally:
            cap.release()

    def _publish(self, frame: np.ndarray) -> None:
        if self._mirror:
            frame = cv2.flip(frame, 1)
        with self._cond:
            self._frame, self._stamp = frame, time.time()
            self._seq += 1
            self._cond.notify_all()

    # ── consumer API ─────────────────────────────────────────────────────────

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


# ── discovery ────────────────────────────────────────────────────────────────

_VIRTUAL_HINTS = ("virtual", "obs", "snap camera", "xsplit", "nvidia broadcast")


def device_names() -> List[str]:
    """
    Friendly names via DirectShow, in MSMF index order. MSMF only lists
    physical devices while DirectShow also lists virtual cameras (OBS…), so
    those are dropped to keep the order aligned.
    """
    if sys.platform != "win32":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph
        names = FilterGraph().get_input_devices()
    except Exception:
        return []
    return [n for n in names if not any(h in n.lower() for h in _VIRTUAL_HINTS)]


def list_cameras(active: Optional[int] = None, max_index: int = 4) -> List[Dict[str, object]]:
    """
    Available cameras. Never reopens `active` (the camera in use): with MSMF a
    second open of the same device can kill the running stream. On Windows the
    names list is enough and nothing is opened at all.
    """
    names = device_names()
    if names:
        return [{"index": i, "name": n} for i, n in enumerate(names)]

    found: List[Dict[str, object]] = []
    for idx in range(max_index):
        if idx == active:
            found.append({"index": idx, "name": f"Cámara {idx}"})
            continue
        cap = cv2.VideoCapture(idx, BACKENDS[0][1])
        if cap.isOpened():
            found.append({"index": idx, "name": f"Cámara {idx}"})
        cap.release()
    return found


def resolve_device(cfg: CameraConfig) -> int:
    """Prefer the remembered camera name: indexes shift when devices are plugged in."""
    if cfg.name:
        names = device_names()
        if cfg.name in names:
            return names.index(cfg.name)
    return cfg.device

from __future__ import annotations

import numpy as np
import pytest

from gesturekey.config import CameraConfig
from gesturekey.vision import camera as cam_mod
from gesturekey.vision.camera import Camera, CameraError


class FakeCapture:
    behaviour = {}   # backend id → "ok" | "silent" | "closed"

    def __init__(self, index, backend):
        self.mode = FakeCapture.behaviour.get(backend, "closed")

    def isOpened(self):
        return self.mode != "closed"

    def set(self, *a):
        return True

    def get(self, prop):
        return 0.0

    def read(self):
        if self.mode == "ok":
            return True, np.zeros((4, 4, 3), np.uint8)
        return False, None

    def release(self):
        pass


@pytest.fixture
def fake_cv(monkeypatch):
    monkeypatch.setattr(cam_mod.cv2, "VideoCapture", FakeCapture)
    monkeypatch.setattr(cam_mod, "FIRST_FRAME_TIMEOUT", 0.2)
    monkeypatch.setattr(cam_mod, "BACKENDS", [("A", 1), ("B", 2)])
    return FakeCapture


def test_opened_but_silent_device_is_busy(fake_cv):
    fake_cv.behaviour = {1: "silent", 2: "silent"}
    with pytest.raises(CameraError) as err:
        Camera(CameraConfig())
    assert err.value.reason == "busy"


def test_no_device_is_missing(fake_cv):
    fake_cv.behaviour = {}
    with pytest.raises(CameraError) as err:
        Camera(CameraConfig())
    assert err.value.reason == "missing"


def test_falls_back_to_the_next_backend(fake_cv):
    fake_cv.behaviour = {1: "closed", 2: "ok"}
    cam = Camera(CameraConfig())
    assert cam.backend == "B"
    assert cam.read(timeout=1.0) is not None
    cam.release()

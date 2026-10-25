"""The engine loop end to end, with a fake camera and tracker (no webcam needed)."""
from __future__ import annotations
import time

import numpy as np
from conftest import make_hand

from gesturekey.config import AppConfig
from gesturekey.runtime import engine as engine_mod


class FakeCamera:
    def __init__(self, cfg):
        self.device, self.actual = cfg.device, (1280, 720, 60.0)

    def read(self, timeout=1.0):
        time.sleep(1 / 60)
        return np.zeros((720, 1280, 3), np.uint8), time.time()

    def release(self):
        pass


class FakeTracker:
    """Two open palms, held still: exercises classifier, state filter and power."""

    def __init__(self, cfg):
        pass

    def process(self, frame, t):
        return {"Left": make_hand((0.3, 0.6), side="Left"), "Right": make_hand((0.7, 0.6))}

    def release(self):
        pass


def test_engine_loop_emits_frames_with_the_new_fields(monkeypatch):
    monkeypatch.setattr(engine_mod, "Camera", FakeCamera)
    monkeypatch.setattr(engine_mod, "HandTracker", FakeTracker)
    msgs = []
    eng = engine_mod.Engine(AppConfig(), msgs.append, persist=False)
    eng.start()
    deadline = time.time() + 15
    while time.time() < deadline and sum(m["type"] == "frame" for m in msgs) < 30:
        time.sleep(0.05)
    eng.stop()

    errors = [m for m in msgs if m["type"] == "status" and m["level"] == "error"]
    assert not errors, errors
    frames = [m for m in msgs if m["type"] == "frame"]
    assert len(frames) >= 30
    last = frames[-1]
    for key in ("state", "raw_state", "confidence", "hands", "owner", "owner_info", "arming", "enabled", "fps"):
        assert key in last
    assert len(last["hands"]) == 2

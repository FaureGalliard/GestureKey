"""The engine loop end to end, with a fake camera and tracker (no webcam needed)."""
from __future__ import annotations
import time

import numpy as np
import pytest
from conftest import make_hand

from gesturekey.config import AppConfig
from gesturekey.runtime import engine as engine_mod
from gesturekey.vision.camera import CameraError


class FakeCamera:
    """Scriptable camera: `plan` decides what each open does; `stall_after` stops frames."""
    plan: list = []
    stall_after = None
    opened = 0

    def __init__(self, cfg, device=None):
        FakeCamera.opened += 1
        outcome = FakeCamera.plan.pop(0) if FakeCamera.plan else "ok"
        if outcome != "ok":
            raise CameraError("fake", outcome)
        self.device = cfg.device if device is None else device
        self.actual, self.backend = (1280, 720, 60.0), "FAKE"
        self.last_frame_at, self._frames = time.time(), 0

    def read(self, timeout=1.0):
        time.sleep(1 / 60)
        if FakeCamera.stall_after is not None and self._frames >= FakeCamera.stall_after:
            return None
        self._frames += 1
        self.last_frame_at = time.time()
        return np.zeros((720, 1280, 3), np.uint8), self.last_frame_at

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


@pytest.fixture
def fakes(monkeypatch):
    FakeCamera.plan, FakeCamera.stall_after, FakeCamera.opened = [], None, 0
    monkeypatch.setattr(engine_mod, "Camera", FakeCamera)
    monkeypatch.setattr(engine_mod, "HandTracker", FakeTracker)
    monkeypatch.setattr(engine_mod, "RETRY_GAP_S", 0.01)
    monkeypatch.setattr(engine_mod, "RETRY_S", 0.2)
    monkeypatch.setattr(engine_mod, "STALL_S", 0.3)
    monkeypatch.setattr(engine_mod, "device_names", lambda: ["Fake Cam"])
    monkeypatch.setattr(engine_mod, "resolve_device", lambda cfg: 0)
    monkeypatch.setattr(engine_mod, "list_cameras", lambda active=None: [{"index": 0, "name": "Fake Cam"}])


def _run(until, seconds=15):
    msgs = []
    eng = engine_mod.Engine(AppConfig(), msgs.append, persist=False)
    eng.start()
    deadline = time.time() + seconds
    while time.time() < deadline and not until(msgs):
        time.sleep(0.05)
    eng.stop()
    return msgs


def _frames(msgs):
    return [m for m in msgs if m["type"] == "frame"]


def _statuses(msgs):
    return [m["status"] for m in msgs if m["type"] == "camera_status"]


def test_engine_loop_emits_frames_with_the_new_fields(fakes):
    msgs = _run(lambda m: len(_frames(m)) >= 30)
    errors = [m for m in msgs if m["type"] == "status" and m["level"] == "error"]
    assert not errors, errors
    last = _frames(msgs)[-1]
    for key in ("state", "raw_state", "confidence", "hands", "owner", "owner_info", "arming", "enabled", "fps"):
        assert key in last
    assert len(last["hands"]) == 2
    assert _statuses(msgs)[:2] == ["opening", "ok"]


def test_busy_camera_at_start_heals_by_itself(fakes):
    FakeCamera.plan = ["busy"] * 4          # e.g. the previous engine still releasing it
    msgs = _run(lambda m: len(_frames(m)) >= 5)
    assert "busy" in _statuses(msgs)
    assert _statuses(msgs)[-1] == "ok"
    assert len(_frames(msgs)) >= 5


def test_stalled_camera_reconnects(fakes):
    FakeCamera.stall_after = 10             # stream dies after 10 frames
    msgs = _run(lambda m: "reconnecting" in _statuses(m) and _statuses(m)[-1] == "ok", seconds=10)
    assert "reconnecting" in _statuses(msgs)
    assert FakeCamera.opened >= 2


def test_listing_cameras_does_not_touch_the_active_one(fakes, monkeypatch):
    seen = {}
    monkeypatch.setattr(engine_mod, "list_cameras",
                        lambda active=None: seen.setdefault("active", active) and [] or [])
    msgs = []
    eng = engine_mod.Engine(AppConfig(), msgs.append, persist=False)
    eng.start()
    while not _frames(msgs):
        time.sleep(0.05)
    eng.command({"cmd": "list_cameras"})
    deadline = time.time() + 5
    while "active" not in seen and time.time() < deadline:
        time.sleep(0.05)
    eng.stop()
    assert seen["active"] == 0              # the engine tells discovery which device to leave alone

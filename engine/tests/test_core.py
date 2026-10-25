from __future__ import annotations
import json

from gesturekey.actions.executor import ActionExecutor
from gesturekey.actions.types import Hotkey, WindowMove
from gesturekey.config import AppConfig
from gesturekey.core.filters import OneEuroFilter


def test_config_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    cfg = AppConfig()
    cfg.camera.device = 2
    cfg.gestures.grab_window.speed = 1.7
    cfg.save(path)
    loaded = AppConfig.load(path)
    assert loaded.camera.device == 2
    assert loaded.gestures.grab_window.speed == 1.7


def test_config_merge_ignores_junk():
    cfg = AppConfig()
    cfg.merge({"camera": {"device": "3", "fps": True, "nope": 1},
               "gestures": {"zoom": {"enabled": "yes"}}, "bogus": {}})
    assert cfg.camera.device == 3
    assert cfg.camera.fps == 60            # bool is not an int here
    assert cfg.gestures.zoom.enabled is True


def test_legacy_settings_file_keeps_camera(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"camera_device": 1}))   # v2 format
    assert AppConfig.load(path).camera.device == 0      # ignored, no crash


def test_one_euro_smooths_still_signal():
    f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    values = [f(0.5 + (0.01 if i % 2 else -0.01), i / 60) for i in range(120)]
    assert max(values[60:]) - min(values[60:]) < 0.01


def test_executor_coalesces_moves():
    ex = ActionExecutor()
    ran = []
    ex._run = ran.append   # type: ignore[method-assign]
    ex.submit([Hotkey(("win",)), *[WindowMove(0.01, 0.0)] * 5, Hotkey(("tab",))])
    ex.stop()
    moves = [a for a in ran if isinstance(a, WindowMove)]
    assert sum(m.dx for m in moves) == 0.05
    assert isinstance(ran[0], Hotkey) and isinstance(ran[-1], Hotkey)

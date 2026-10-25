from __future__ import annotations
import random

from conftest import make_hand

from gesturekey.runtime.recorder import Recorder
from gesturekey.tools.analyze import report


def _frame(t, state, hand, conf=0.9):
    return {
        "type": "frame", "t": t, "state": state, "raw_state": state, "confidence": conf,
        "hands": [{"side": hand.side, "score": 1.0, "landmarks": [list(p) for p in hand.img]}] if hand else [],
        "owner": None, "paused": False, "fps": 30.0,
    }


def test_recorder_and_analyzer(tmp_path, capsys):
    rng = random.Random(0)
    rec = Recorder(tmp_path / "s.jsonl")
    rec.write({"type": "camera", "device": 0, "width": 1280, "height": 720, "fps": 60})
    rec.write({"type": "preview", "jpeg": "x"})            # not recorded
    t = 0.0
    for _ in range(120):                                    # 4 s palm held still, with noise
        jitter = (0.5 + rng.gauss(0, 0.002), 0.7 + rng.gauss(0, 0.002))
        rec.write(_frame(t, "PALM", make_hand(jitter)))
        t += 1 / 30
    for _ in range(30):
        rec.write(_frame(t, "NO HANDS", None, 1.0))
        t += 1 / 30
    rec.write({"type": "event", "event": "SCROLL", "t": t})
    rec.close()

    report(tmp_path / "s.jsonl")
    out = capsys.readouterr().out
    assert "cámara 1280×720" in out
    assert "PALM" in out and " px" in out          # the hold was found and measured
    assert "SCROLL" in out
    assert "preview" not in (tmp_path / "s.jsonl").read_text()

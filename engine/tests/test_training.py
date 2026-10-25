"""Training data round trip and the movement CSV export."""
from __future__ import annotations
import csv
import json

from conftest import make_hand

from gesturekey.tools.dataset import append_rows, read, row
from gesturekey.tools.export import export
from gesturekey.vision.classifier import feature_vector


def test_dataset_round_trip_gives_the_live_features(tmp_path):
    hands = {"Right": make_hand((0.6, 0.5), tilt=10)}
    path = tmp_path / "session-x.csv"
    append_rows(path, [row("s1", 1.0, "PALM", (1280, 720), hands)])
    [(session, label, features)] = list(read(path))
    assert (session, label) == ("s1", "PALM")
    live = feature_vector(hands)
    assert max(abs(a - b) for a, b in zip(features, live)) < 0.1   # angles are in degrees; 5-decimal coordinates


def test_legacy_feature_csv_is_readable():
    from pathlib import Path
    legacy = Path(__file__).resolve().parents[1] / "training" / "data" / "legacy_v2_features.csv"
    first = next(iter(read(legacy)))
    assert first[0] == "legacy" and len(first[2]) == 20


def test_export_movements(tmp_path):
    hand = make_hand((0.4, 0.5), tilt=-45)
    src = tmp_path / "s.jsonl"
    msgs = [{"type": "frame", "t": 10.0, "state": "PALM", "raw_state": "PALM", "confidence": 0.9,
             "owner": "GRAB_WINDOW", "hands": [{"side": "Right", "landmarks": [list(p) for p in hand.img]}]},
            {"type": "event", "event": "WINDOW_TO_MONITOR", "t": 10.0}]
    src.write_text("\n".join(json.dumps(m) for m in msgs), encoding="utf-8")
    dst = tmp_path / "s.csv"
    assert export(src, dst) == 1
    rec = next(csv.DictReader(dst.open(encoding="utf-8")))
    assert rec["owner"] == "GRAB_WINDOW" and rec["events"] == "WINDOW_TO_MONITOR"
    assert abs(float(rec["right_tilt_deg"]) + 45) < 1

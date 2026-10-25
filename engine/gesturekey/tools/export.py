"""
Export a recorded session (see runtime/recorder.py) as a CSV of movements.

    uv run python -m gesturekey.tools.export --latest            # → next to the recording
    uv run python -m gesturekey.tools.export <session.jsonl> [-o out.csv]

One row per frame: time, filtered/raw state, confidence, gesture owning the
hand, events fired on that frame, and per hand the wrist, palm centre, palm
length, tilt (0 = fingers up, + = towards the user's right) and all 21
landmarks. Open it in a spreadsheet or plot it to show how a gesture moves.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List

from gesturekey.tools.analyze import _latest

N = 21
SIDES = ("Left", "Right")


def _hand_cols(side: str) -> List[str]:
    s = side.lower()
    cols = [f"{s}_wrist_x", f"{s}_wrist_y", f"{s}_palm_x", f"{s}_palm_y", f"{s}_palm_len", f"{s}_tilt_deg"]
    return cols + [f"{s}_{a}{i}" for i in range(N) for a in ("x", "y")]


def _hand_values(lm: List[List[float]]) -> List[object]:
    (x0, y0), (x9, y9) = lm[0], lm[9]
    px = sum(lm[i][0] for i in (0, 5, 9, 13, 17)) / 5
    py = sum(lm[i][1] for i in (0, 5, 9, 13, 17)) / 5
    tilt = math.degrees(math.atan2(x9 - x0, -(y9 - y0)))
    vals: List[object] = [x0, y0, round(px, 4), round(py, 4), round(math.hypot(x9 - x0, y9 - y0), 4), round(tilt, 1)]
    for x, y in lm:
        vals += [x, y]
    return vals


def export(src: Path, dst: Path) -> int:
    frames: List[dict] = []
    events_at: Dict[float, List[str]] = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "frame":
            frames.append(msg)
        elif msg.get("type") == "event":
            events_at.setdefault(msg["t"], []).append(msg["event"])

    cols = ["t", "state", "raw_state", "confidence", "owner", "events"]
    for side in SIDES:
        cols += _hand_cols(side)
    t0 = frames[0]["t"] if frames else 0.0
    with dst.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for f in frames:
            hands = {h["side"]: h["landmarks"] for h in f["hands"]}
            out: List[object] = [round(f["t"] - t0, 3), f["state"], f["raw_state"], f["confidence"],
                                 f.get("owner") or "", "|".join(events_at.get(f["t"], []))]
            for side in SIDES:
                out += _hand_values(hands[side]) if side in hands else [""] * len(_hand_cols(side))
            w.writerow(out)
    return len(frames)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.export")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("-o", "--out", type=Path)
    args = parser.parse_args()
    src = _latest() if args.latest or not args.path else args.path
    dst = args.out or src.with_suffix(".csv")
    n = export(src, dst)
    print(f"{n} frames → {dst}")


if __name__ == "__main__":
    main()

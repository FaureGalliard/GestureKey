"""
Record labelled hand poses for training.

    uv run python -m gesturekey.tools.collect [--out training/data] [--camera 0]

Keys:  1 PALM  2 FIST  3 PINCH  4 TWO_FINGERS  5 THREE_FINGERS  6 FOUR_FINGERS
       7 POINT  9 THUMB_DOWN  0 OTHER (relaxed / in between)
       SPACE start/stop recording the selected pose     q quit

Record each pose in several short takes: both hands, near and far, tilted,
in different light. Every run is its own session (one CSV), which is what
lets tools.train evaluate on sessions it never saw.
"""
from __future__ import annotations
import argparse
import time
from collections import Counter
from pathlib import Path

import cv2

from gesturekey.config import AppConfig
from gesturekey.tools.dataset import LABEL_KEYS, append_rows, data_dir, row
from gesturekey.vision.camera import Camera
from gesturekey.vision.tracker import HandTracker

_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
          (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17),
          (17, 18), (18, 19), (19, 20)]


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.collect")
    parser.add_argument("--out", type=Path, default=None, help="folder for the session CSV")
    parser.add_argument("--camera", type=int, default=None, help="camera index (default: from settings)")
    args = parser.parse_args()

    cfg = AppConfig.load()
    session = time.strftime("%Y%m%d-%H%M%S")
    path = data_dir(args.out) / f"session-{session}.csv.gz"   # ~5× smaller, fine for git
    camera = Camera(cfg.camera, device=args.camera)
    tracker = HandTracker(cfg.tracking, mirrored=cfg.camera.mirror)
    label, recording, pending, counts = "PALM", False, [], Counter()
    print(f"Writing {path}")
    try:
        while True:
            got = camera.read(timeout=1.0)
            if got is None:
                continue
            frame, stamp = got
            hands = tracker.process(frame, stamp)
            h, w = frame.shape[:2]
            if recording and hands:
                pending.append(row(session, stamp, label, (w, h), hands))
                counts[label] += 1
                if len(pending) >= 30:
                    append_rows(path, pending)
                    pending.clear()

            view = frame.copy()
            for hand in hands.values():
                pts = [(int(x * w), int(y * h)) for x, y in hand.img]
                for a, b in _BONES:
                    cv2.line(view, pts[a], pts[b], (220, 220, 220), 2, cv2.LINE_AA)
            status = f"{'REC ' if recording else ''}{label}   hands: {len(hands)}"
            cv2.putText(view, status, (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                        (60, 60, 255) if recording else (255, 255, 255), 2, cv2.LINE_AA)
            summary = "  ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
            cv2.putText(view, summary, (16, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.imshow("GestureKey collect — 1-7 9 0 choose pose, SPACE record, q quit", view)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                recording = not recording
            elif chr(key) in LABEL_KEYS:
                label, recording = LABEL_KEYS[chr(key)], False
    finally:
        if pending:
            append_rows(path, pending)
        camera.release()
        tracker.release()
        cv2.destroyAllWindows()
        print(f"Saved {sum(counts.values())} frames: {dict(counts)}")


if __name__ == "__main__":
    main()

"""
Run a video file through the real pipeline (tracker → classifier → state
filter → gestures) without performing any action, and print what fires.

    uv run python -m gesturekey.tools.replay <video.mp4> [--no-mirror] [--trace]

Useful to check a gesture recorded with the camera app before tuning it.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import cv2

from gesturekey.config import AppConfig
from gesturekey.core.types import FrameData, HandState
from gesturekey.gestures.arbiter import GestureArbiter
from gesturekey.runtime.engine import MODEL_PATH
from gesturekey.vision.classifier import StateClassifier
from gesturekey.vision.states import StateFilter
from gesturekey.vision.tracker import HandTracker


def replay(path: Path, mirror: bool = True, trace: bool = False) -> list:
    cfg = AppConfig()
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    tracker = HandTracker(cfg.tracking, mirrored=mirror)
    classifier = StateClassifier(MODEL_PATH)
    states = StateFilter(classifier.classes, cfg.states)
    arbiter = GestureArbiter(cfg.gestures)
    fired, i, last_state = [], 0, None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = i / fps
        i += 1
        if mirror:
            frame = cv2.flip(frame, 1)
        hands = tracker.process(frame, t)
        proba = classifier.predict_proba(hands) if hands else None
        raw = max(proba, key=proba.__getitem__) if proba else HandState.NO_HANDS.value
        state = states.update(proba, t)
        out = arbiter.process(FrameData(state=state, hands=hands, timestamp=t,
                                        raw_state=_state(raw), raw_confidence=max(proba.values()) if proba else 1.0))
        if trace and state != last_state:
            print(f"{t:6.2f}s  state {state.value}")
        last_state = state
        for event in out.events:
            fired.append((round(t, 2), event.value, [type(a).__name__ + str(getattr(a, "direction", "")) for a in out.actions]))
            print(f"{t:6.2f}s  {event.value:<22} {fired[-1][2]}")
    tracker.release()
    return fired


def _state(name: str) -> HandState:
    try:
        return HandState(name)
    except ValueError:
        return HandState.UNKNOWN


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.replay")
    parser.add_argument("video", type=Path)
    parser.add_argument("--no-mirror", action="store_true", help="the video is already mirrored")
    parser.add_argument("--trace", action="store_true", help="also print every state change")
    args = parser.parse_args()
    replay(args.video, mirror=not args.no_mirror, trace=args.trace)


if __name__ == "__main__":
    main()

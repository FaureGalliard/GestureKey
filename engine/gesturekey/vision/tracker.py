from __future__ import annotations
import math
from typing import Dict, List

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

from gesturekey.config import TrackingConfig, resource_path
from gesturekey.core.filters import OneEuroFilter, PointFilter
from gesturekey.core.geometry import dist
from gesturekey.core.types import Hand, Point

KEEP_SIDE_RADIUS = 0.20   # a lone hand this close to where it was keeps its side label
LANDMARKER_PATH  = resource_path("models/hand_landmarker.task")


class _HandSmoother:
    """One Euro filter per landmark (x, y and depth) for one hand."""

    def __init__(self, cfg: TrackingConfig) -> None:
        self._xy = [PointFilter(cfg.filter_min_cutoff, cfg.filter_beta) for _ in range(21)]
        self._z  = [OneEuroFilter(cfg.filter_min_cutoff, cfg.filter_beta) for _ in range(21)]

    def __call__(self, img: List[Point], z: List[float], t: float):
        return ([f(p, t) for f, p in zip(self._xy, img)],
                [f(v, t) for f, v in zip(self._z, z)])


class HandTracker:
    """
    MediaPipe HandLandmarker (Tasks API) → {"Right": Hand, "Left": Hand}.
    Expects a mirrored frame and a timestamp per frame (VIDEO mode tracks hands
    between frames instead of detecting them again every time).

    Landmarks are smoothed here, once, for every consumer (classifier and
    gestures). Side labels are kept stable across frames, and each side keeps
    its own filter state.
    """

    def __init__(self, cfg: TrackingConfig, max_num_hands: int = 2, mirrored: bool = True) -> None:
        self._cfg = cfg
        #: the frame is a mirror (selfie) view. HandLandmarker labels handedness as if it
        #: weren't (measured: the user's right hand comes out "Left"), so swap then.
        self.mirrored = mirrored
        options = HandLandmarkerOptions(
            # from bytes, not a path: MediaPipe mishandles paths with non-ASCII characters
            base_options=BaseOptions(model_asset_buffer=LANDMARKER_PATH.read_bytes()),
            running_mode=RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=cfg.min_detection_confidence,
            min_hand_presence_confidence=cfg.min_presence_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
        )
        self._landmarker = HandLandmarker.create_from_options(options)
        self._last_ms = -1
        self._smoothers: Dict[str, _HandSmoother] = {}
        self._last_wrist: Dict[str, Point] = {}

    def process(self, frame: np.ndarray, t: float) -> Dict[str, Hand]:
        h, w = frame.shape[:2]
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ms = max(int(t * 1000), self._last_ms + 1)      # VIDEO mode needs strictly increasing timestamps
        self._last_ms = ms
        result = self._landmarker.detect_for_video(image, ms)
        if not result.hand_landmarks:
            self._smoothers.clear()
            self._last_wrist.clear()
            return {}

        raw = []
        worlds = result.hand_world_landmarks or [None] * len(result.hand_landmarks)
        for lms, handed, world in zip(result.hand_landmarks, result.handedness, worlds):
            cls = handed[0]
            label = cls.category_name
            if self.mirrored:
                label = "Left" if label == "Right" else "Right"
            wl = tuple((p.x, p.y, p.z) for p in world) if world is not None else ()
            raw.append((label, cls.score, [(lm.x, lm.y) for lm in lms], [lm.z for lm in lms], wl))

        sides = self._assign_sides([(label, img[0]) for label, _, img, _, _ in raw])

        hands: Dict[str, Hand] = {}
        for side, (_, score, img, z, world) in zip(sides, raw):
            smoother = self._smoothers.get(side) or self._smoothers.setdefault(side, _HandSmoother(self._cfg))
            img_f, z_f = smoother(img, z, t)
            hands[side] = Hand(side=side, norm=_normalise([(x * w, y * h) for x, y in img_f]),
                               img=img_f, z=z_f, score=score, world=world)

        for side in list(self._smoothers):
            if side not in hands:
                del self._smoothers[side]
        self._last_wrist = {side: hand.wrist for side, hand in hands.items()}
        return hands

    def _assign_sides(self, detections: List[tuple]) -> List[str]:
        labels = [label for label, _ in detections]
        if len(detections) == 2:
            if labels[0] == labels[1]:
                # same label twice: trust position (right of the mirrored image = user's right)
                order = sorted(range(2), key=lambda i: detections[i][1][0])
                out = ["", ""]
                out[order[0]], out[order[1]] = "Left", "Right"
                return out
            return labels
        # one hand: keep its previous side if it hasn't jumped, so the label doesn't flicker
        wrist = detections[0][1]
        if len(self._last_wrist) == 1:
            (prev_side, prev_wrist), = self._last_wrist.items()
            if dist(wrist, prev_wrist) < KEEP_SIDE_RADIUS:
                return [prev_side]
        return labels

    def release(self) -> None:
        self._landmarker.close()


def _normalise(landmarks: List[Point]) -> List[Point]:
    """Wrist-centred, scaled by wrist → middle MCP (pixel space keeps aspect)."""
    x0, y0   = landmarks[0]
    centered = [(x - x0, y - y0) for x, y in landmarks]
    scale    = math.hypot(*centered[9]) or 1.0
    return [(x / scale, y / scale) for x, y in centered]


from __future__ import annotations
import math
from typing import Dict, List

import cv2
import mediapipe as mp
import numpy as np

from gesturekey.config import TrackingConfig
from gesturekey.core.filters import OneEuroFilter, PointFilter
from gesturekey.core.geometry import dist
from gesturekey.core.types import Hand, Point

KEEP_SIDE_RADIUS = 0.20   # a lone hand this close to where it was keeps its side label


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
    MediaPipe Hands → {"Right": Hand, "Left": Hand}. Expects a mirrored frame.

    Landmarks are smoothed here, once, for every consumer (classifier and
    gestures). Side labels are kept stable across frames, and each side keeps
    its own filter state.
    """

    def __init__(self, cfg: TrackingConfig, max_num_hands: int = 2) -> None:
        self._cfg = cfg
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
        )
        self._smoothers: Dict[str, _HandSmoother] = {}
        self._last_wrist: Dict[str, Point] = {}

    def process(self, frame: np.ndarray, t: float) -> Dict[str, Hand]:
        h, w = frame.shape[:2]
        results = self._hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_hand_landmarks:
            self._smoothers.clear()
            self._last_wrist.clear()
            return {}

        raw = []
        for lms, handed in zip(results.multi_hand_landmarks, results.multi_handedness):
            cls = handed.classification[0]
            raw.append((cls.label, cls.score, [(lm.x, lm.y) for lm in lms.landmark], [lm.z for lm in lms.landmark]))

        sides = self._assign_sides([(label, img[0]) for label, _, img, _ in raw])

        hands: Dict[str, Hand] = {}
        for side, (_, score, img, z) in zip(sides, raw):
            smoother = self._smoothers.get(side) or self._smoothers.setdefault(side, _HandSmoother(self._cfg))
            img_f, z_f = smoother(img, z, t)
            hands[side] = Hand(side=side, norm=_normalise([(x * w, y * h) for x, y in img_f]),
                               img=img_f, z=z_f, score=score)

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
        self._hands.close()


def _normalise(landmarks: List[Point]) -> List[Point]:
    """Wrist-centred, scaled by wrist → middle MCP (pixel space keeps aspect)."""
    x0, y0   = landmarks[0]
    centered = [(x - x0, y - y0) for x, y in landmarks]
    scale    = math.hypot(*centered[9]) or 1.0
    return [(x / scale, y / scale) for x, y in centered]


from __future__ import annotations
import math
from typing import Dict, List

import cv2
import mediapipe as mp
import numpy as np

from gesturekey.config import TrackingConfig
from gesturekey.core.types import Hand, Point


class HandTracker:
    """MediaPipe Hands → {"Right": Hand, "Left": Hand}. Expects a mirrored frame."""

    def __init__(self, cfg: TrackingConfig, max_num_hands: int = 2) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
        )

    def process(self, frame: np.ndarray) -> Dict[str, Hand]:
        h, w = frame.shape[:2]
        results = self._hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_hand_landmarks:
            return {}

        hands: List[Hand] = []
        for lms, handed in zip(results.multi_hand_landmarks, results.multi_handedness):
            cls = handed.classification[0]
            img = [(lm.x, lm.y) for lm in lms.landmark]
            hands.append(Hand(
                side=cls.label,             # correct for a mirrored (selfie) image
                norm=_normalise([(x * w, y * h) for x, y in img]),
                img=img,
                z=[lm.z for lm in lms.landmark],
                score=cls.score,
            ))

        # Two hands with the same label: trust position instead (right of the
        # mirrored image is the user's right hand).
        if len(hands) == 2 and hands[0].side == hands[1].side:
            left, right = sorted(hands, key=lambda hd: hd.wrist[0])
            hands = [_with_side(left, "Left"), _with_side(right, "Right")]

        return {hd.side: hd for hd in hands}

    def release(self) -> None:
        self._hands.close()


def _with_side(hand: Hand, side: str) -> Hand:
    return Hand(side=side, norm=hand.norm, img=hand.img, z=hand.z, score=hand.score)


def _normalise(landmarks: List[Point]) -> List[Point]:
    """Wrist-centred, scaled by wrist → middle MCP (pixel space keeps aspect)."""
    x0, y0   = landmarks[0]
    centered = [(x - x0, y - y0) for x, y in landmarks]
    scale    = math.hypot(*centered[9]) or 1.0
    return [(x / scale, y / scale) for x, y in centered]

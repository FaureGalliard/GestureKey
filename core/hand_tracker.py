"""
HandTracker — encapsulates all MediaPipe logic and landmark processing.
The rest of the application never imports mediapipe directly.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mediapipe as mp

from domain.models import HandsData, HandsRaw, Landmark2D


class HandTracker:
    """
    Processes a BGR frame and returns normalised hand landmarks
    (geometry-normalised so features are scale/translation invariant)
    plus the raw MediaPipe objects (needed for Z-depth gestures).

    Parameters
    ----------
    max_num_hands : int
    min_detection_confidence : float
    min_tracking_confidence : float
    """

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.1,
        min_tracking_confidence: float = 0.1,
    ) -> None:
        self._mp_hands = mp.solutions.hands
        self._mp_draw  = mp.solutions.drawing_utils
        self._hands    = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    # ------------------------------------------------------------------
    def process(self, frame: Any) -> Tuple[HandsData, HandsRaw]:
        """
        Parameters
        ----------
        frame : np.ndarray
            BGR frame from OpenCV.

        Returns
        -------
        (hands_data, hands_raw)
            hands_data  : geometry-normalised landmark lists per side.
            hands_raw   : raw mp.solutions.hands objects per side (for depth).
        """
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        # Draw landmarks onto the original frame (mutates frame in-place)
        raw_list: List[Any] = []
        pixel_list: List[List[Landmark2D]] = []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    frame, hand_landmarks, self._mp_hands.HAND_CONNECTIONS
                )
                pixel_coords = [(lm.x * w, lm.y * h) for lm in hand_landmarks.landmark]
                pixel_list.append(pixel_coords)
                raw_list.append(hand_landmarks)

        # Assign left / right by X position (leftmost wrist → "Right" hand
        # in mirror-view; rightmost → "Left")
        hands_data: HandsData = {}
        hands_raw:  HandsRaw  = {}

        if len(pixel_list) == 1:
            wrist_x = pixel_list[0][0][0]
            side = "Right" if wrist_x < w // 2 else "Left"
            hands_data[side] = self._normalise(pixel_list[0])
            hands_raw[side]  = raw_list[0]

        elif len(pixel_list) == 2:
            paired = sorted(zip(pixel_list, raw_list), key=lambda p: p[0][0][0])
            hands_data["Right"] = self._normalise(paired[0][0])
            hands_data["Left"]  = self._normalise(paired[1][0])
            hands_raw["Right"]  = paired[0][1]
            hands_raw["Left"]   = paired[1][1]

        return hands_data, hands_raw

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise(landmarks: List[Landmark2D]) -> List[Landmark2D]:
        """
        Translate so the wrist is the origin, then scale so that the
        wrist→middle-MCP distance equals 1.
        """
        x0, y0 = landmarks[0]
        centered = [(x - x0, y - y0) for x, y in landmarks]
        sx, sy = centered[9]
        scale = math.hypot(sx, sy) or 1.0
        return [(x / scale, y / scale) for x, y in centered]

    def release(self) -> None:
        self._hands.close()
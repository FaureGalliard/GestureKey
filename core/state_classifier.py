"""
StateClassifier — wraps the Random Forest model.
No buffer, no consensus — just predict().
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from domain.enums import HandState

# ---- feature definition --------------------------------------------------
FINGERS = {
    "THUMB":  [1, 2, 4],
    "INDEX":  [5, 6, 8],
    "MIDDLE": [9, 10, 12],
    "RING":   [13, 14, 16],
    "PINKY":  [17, 18, 20],
}

_SIDES = ["left", "right"]
_FEATURE_NAMES: List[str] = []
for side in _SIDES:
    for finger in FINGERS:
        _FEATURE_NAMES.append(f"{side}_{finger}_dist")
for side in _SIDES:
    for finger in FINGERS:
        _FEATURE_NAMES.append(f"{side}_{finger}_angle")

# Reorder to match original training schema:
# left_dists, left_angles, right_dists, right_angles
FEATURE_NAMES = (
    [f"left_{f}_dist"  for f in FINGERS]
    + [f"left_{f}_angle" for f in FINGERS]
    + [f"right_{f}_dist"  for f in FINGERS]
    + [f"right_{f}_angle" for f in FINGERS]
)


# ---- geometry helpers (no external deps) ---------------------------------
def _dist(a: tuple, b: tuple) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle(a: tuple, b: tuple, c: tuple) -> float:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag = math.hypot(*ba) * math.hypot(*bc)
    if mag == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / mag))))


def _extract_features(landmarks: Optional[List]) -> List[float]:
    if not landmarks or landmarks[0] == (-1.0, -1.0):
        return [0.0] * 10
    wrist = landmarks[0]
    dists  = [_dist(wrist, landmarks[f[2]]) for f in FINGERS.values()]
    angles = [_angle(landmarks[f[0]], landmarks[f[1]], landmarks[f[2]]) for f in FINGERS.values()]
    return dists + angles


# ---- classifier -----------------------------------------------------------
class StateClassifier:
    """
    Wraps the trained scikit-learn model.

    Parameters
    ----------
    model_path : Path
        Path to the serialised Random Forest (.pkl).
    """

    def __init__(self, model_path: Path) -> None:
        self._model = joblib.load(model_path)
        self._model.verbose = 0

    def predict(self, hands_data: Dict[str, List]) -> Tuple[HandState, float]:
        """
        Parameters
        ----------
        hands_data : dict
            Normalised landmark lists keyed by "Left" / "Right".

        Returns
        -------
        (HandState, confidence)
        """
        left_features  = _extract_features(hands_data.get("Left"))
        right_features = _extract_features(hands_data.get("Right"))
        features = left_features + right_features

        X = pd.DataFrame([features], columns=FEATURE_NAMES)
        raw_prediction = self._model.predict(X)[0]
        confidence = float(max(self._model.predict_proba(X)[0]))

        try:
            state = HandState(raw_prediction)
        except ValueError:
            state = HandState.UNKNOWN

        return state, confidence
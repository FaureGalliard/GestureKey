from __future__ import annotations
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np

from gesturekey.core.geometry import angle, dist
from gesturekey.core.types import Hand, HandState, Point

FINGERS = {
    "THUMB":  (1, 2, 4),
    "INDEX":  (5, 6, 8),
    "MIDDLE": (9, 10, 12),
    "RING":   (13, 14, 16),
    "PINKY":  (17, 18, 20),
}

FEATURE_NAMES = (
    [f"left_{f}_dist"    for f in FINGERS]
    + [f"left_{f}_angle"  for f in FINGERS]
    + [f"right_{f}_dist"  for f in FINGERS]
    + [f"right_{f}_angle" for f in FINGERS]
)


def extract_features(landmarks: Optional[List[Point]]) -> List[float]:
    if not landmarks:
        return [0.0] * 10
    wrist  = landmarks[0]
    dists  = [dist(wrist, landmarks[tip]) for _, _, tip in FINGERS.values()]
    angles = [angle(landmarks[a], landmarks[b], landmarks[c]) for a, b, c in FINGERS.values()]
    return dists + angles


def feature_vector(hands: Dict[str, Hand]) -> List[float]:
    left, right = hands.get("Left"), hands.get("Right")
    return (extract_features(left.norm if left else None)
            + extract_features(right.norm if right else None))


class StateClassifier:
    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at: {model_path.absolute()}")
        self._model = joblib.load(model_path)
        self._model.verbose = 0
        self._classes = list(self._model.classes_)

    @property
    def classes(self) -> List[str]:
        return [str(c) for c in self._classes]

    def predict_proba(self, hands: Dict[str, Hand]) -> Dict[str, float]:
        X = np.asarray([feature_vector(hands)], dtype=np.float64)
        with warnings.catch_warnings():
            # model was fitted on a DataFrame; numpy input is ~10× faster
            warnings.filterwarnings("ignore", message="X does not have valid feature names")
            proba = self._model.predict_proba(X)[0]
        return {str(c): float(p) for c, p in zip(self._classes, proba)}

    def predict(self, hands: Dict[str, Hand]) -> Tuple[HandState, float]:
        proba = self.predict_proba(hands)
        best = max(proba, key=proba.__getitem__)
        try:
            state = HandState(best)
        except ValueError:
            state = HandState.UNKNOWN
        return state, proba[best]

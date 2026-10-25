from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

import pytest

from gesturekey.core.types import FrameData, Hand, HandState
from gesturekey.vision.tracker import _normalise

# A rough open-hand shape around the wrist, in image units (0..1).
_SHAPE = [(0.0, 0.0), (0.03, -0.02), (0.05, -0.05), (0.06, -0.08), (0.07, -0.10),
          (0.03, -0.10), (0.03, -0.14), (0.03, -0.17), (0.03, -0.19),
          (0.0, -0.11), (0.0, -0.15), (0.0, -0.18), (0.0, -0.21),
          (-0.02, -0.10), (-0.02, -0.14), (-0.02, -0.17), (-0.02, -0.19),
          (-0.04, -0.09), (-0.04, -0.12), (-0.04, -0.14), (-0.04, -0.16)]


def make_hand(wrist: Tuple[float, float] = (0.5, 0.7), side: str = "Right", scale: float = 1.0,
              tilt: float = 0.0) -> Hand:
    """`tilt` in degrees: 0 = fingers up, + = leaning towards the user's right."""
    a = math.radians(tilt)
    ca, sa = math.cos(a), math.sin(a)
    img = [(wrist[0] + (dx * ca - dy * sa) * scale, wrist[1] + (dx * sa + dy * ca) * scale) for dx, dy in _SHAPE]
    return Hand(side=side, norm=_normalise([(x * 1280, y * 720) for x, y in img]),
                img=img, z=[0.0] * 21)


def make_frame(state: HandState, t: float, wrist=(0.5, 0.7), scale: float = 1.0,
               hands: Optional[Dict[str, Hand]] = None, raw_state: Optional[HandState] = None,
               tilt: float = 0.0) -> FrameData:
    if hands is None:
        hands = {} if state == HandState.NO_HANDS else {"Right": make_hand(wrist, scale=scale, tilt=tilt)}
    return FrameData(state=state, hands=hands, timestamp=t, raw_state=raw_state or state)


class Clock:
    """Feeds frames at a fixed rate and collects events/actions."""

    def __init__(self, arbiter, fps: float = 60.0) -> None:
        self.arbiter, self.t, self.dt = arbiter, 100.0, 1.0 / fps
        self.events: List[str] = []
        self.actions: list = []

    def run(self, state: HandState, seconds: float, wrist=(0.5, 0.7), to=None, scale_to=None, scale=1.0, tilt=0.0):
        n = max(1, round(seconds / self.dt))
        for i in range(n):
            k = (i + 1) / n
            w = wrist if to is None else (wrist[0] + (to[0] - wrist[0]) * k, wrist[1] + (to[1] - wrist[1]) * k)
            s = scale if scale_to is None else scale + (scale_to - scale) * k
            out = self.arbiter.process(make_frame(state, self.t, w, s, tilt=tilt))
            self.events += [e.value for e in out.events]
            self.actions += out.actions
            self.t += self.dt
        return self


@pytest.fixture
def clock():
    from gesturekey.config import GesturesConfig
    from gesturekey.gestures.arbiter import GestureArbiter
    return Clock(GestureArbiter(GesturesConfig()))

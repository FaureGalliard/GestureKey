from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]


class HandState(str, Enum):
    PALM          = "PALM"
    FIST          = "FIST"
    PINCH         = "PINCH"
    TWO_FINGERS   = "TWO_FINGERS"
    THREE_FINGERS = "THREE_FINGERS"
    FOUR_FINGERS  = "FOUR_FINGERS"
    # poses to train next (see engine/training/README.md)
    POINT         = "POINT"          # ☝️ index only — the mouse cursor
    THUMB_DOWN    = "THUMB_DOWN"     # 👎 — mute (recorded, not in the model yet)
    OTHER         = "OTHER"          # relaxed / in between: explicitly "no pose"
    UNKNOWN       = "UNKNOWN"
    NO_HANDS      = "NO HANDS"


class GestureEvent(str, Enum):
    SCROLL               = "SCROLL"
    VOLUME_UP            = "VOLUME_UP"
    VOLUME_DOWN          = "VOLUME_DOWN"
    ZOOM_IN              = "ZOOM_IN"
    ZOOM_OUT             = "ZOOM_OUT"
    SCREENSHOT           = "SCREENSHOT"
    CLOSE_WINDOW         = "CLOSE_WINDOW"
    MUTE_TOGGLE          = "MUTE_TOGGLE"
    TASK_VIEW            = "TASK_VIEW"
    TASK_VIEW_MOVE       = "TASK_VIEW_MOVE"
    TASK_VIEW_OPEN       = "TASK_VIEW_OPEN"
    TASK_VIEW_CLOSED     = "TASK_VIEW_CLOSED"
    MEDIA_PLAY_PAUSE     = "MEDIA_PLAY_PAUSE"
    GRAB_WINDOW_START    = "GRAB_WINDOW_START"
    GRAB_WINDOW_RELEASED = "GRAB_WINDOW_RELEASED"
    WINDOW_TO_MONITOR    = "WINDOW_TO_MONITOR"
    WINDOW_MAXIMIZED     = "WINDOW_MAXIMIZED"
    POWER_OFF            = "POWER_OFF"
    POWER_ON             = "POWER_ON"


@dataclass(frozen=True)
class Hand:
    """
    One tracked hand.

    norm : wrist-centred, scale-normalised landmarks (classifier space; also
           what the v2 gestures were tuned on).
    img  : landmarks in image space, 0..1, already mirrored when the camera
           is mirrored — x grows to the user's right.
    z    : MediaPipe relative depth per landmark.
    """
    side:  str
    norm:  List[Point]
    img:   List[Point]
    z:     List[float]
    score: float = 1.0
    #: MediaPipe world landmarks: metres, centred on the hand, mostly camera- and
    #: distance-independent. Unfiltered; for training data and future features.
    world: Tuple[Tuple[float, float, float], ...] = ()

    @property
    def wrist(self) -> Point:
        return self.img[0]


@dataclass
class FrameData:
    """
    All data relevant to a single processed frame.

    state is the filtered (probabilistic) hand state; raw_state/raw_confidence
    are the classifier's verdict for this very frame — gestures use them to
    notice early that the user is leaving a pose.
    """
    state:          HandState
    hands:          Dict[str, Hand] = field(default_factory=dict)
    timestamp:      float = 0.0
    raw_state:      Optional[HandState] = None
    raw_confidence: float = 1.0

    @property
    def main_hand(self) -> Optional[Hand]:
        return self.hands.get("Right") or self.hands.get("Left")

    @property
    def has_both_hands(self) -> bool:
        return "Left" in self.hands and "Right" in self.hands

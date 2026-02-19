from enum import Enum


class HandState(str, Enum):
    """Possible hand gesture states detected by the classifier."""
    PALM          = "PALM"
    FIST          = "FIST"
    PINCH         = "PINCH"
    TWO_FINGERS   = "TWO_FINGERS"
    THREE_FINGERS = "THREE_FINGERS"
    FOUR_FINGERS  = "FOUR_FINGERS"
    UNKNOWN       = "UNKNOWN"
    NO_HANDS      = "NO HANDS"


class GestureEvent(str, Enum):
    """Events emitted by gesture detectors."""
    SCROLL        = "SCROLL"
    VOLUME_UP     = "VOLUME_UP"
    VOLUME_DOWN   = "VOLUME_DOWN"
    ZOOM_IN       = "ZOOM_IN"
    ZOOM_OUT      = "ZOOM_OUT"
    SCREENSHOT    = "SCREENSHOT"
    CLOSE_WINDOW  = "CLOSE_WINDOW"
    MUTE_TOGGLE   = "MUTE_TOGGLE"
    TASK_VIEW     = "TASK_VIEW"
    PAUSE_TOGGLE_PAUSED  = "PAUSE_TOGGLE_PAUSED"
    PAUSE_TOGGLE_RESUMED = "PAUSE_TOGGLE_RESUMED"
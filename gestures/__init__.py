from gestures.base import Gesture
from gestures.scroll import ScrollGesture
from gestures.volume import VolumeGesture
from gestures.zoom import PinchZoomGesture
from gestures.screenshot import ScreenshotGesture
from gestures.close_window import CloseWindowGesture
from gestures.pause import PauseResumeGesture
from gestures.mute import MuteToggleGesture
from gestures.task_view import TaskViewGesture

__all__ = [
    "Gesture",
    "ScrollGesture",
    "VolumeGesture",
    "PinchZoomGesture",
    "ScreenshotGesture",
    "CloseWindowGesture",
    "PauseResumeGesture",
    "MuteToggleGesture",
    "TaskViewGesture",
]
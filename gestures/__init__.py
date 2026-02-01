"""
Módulos de gestos individuales
"""

from .scroll import ScrollGesture
from .volumen import VolumeGesture
from .zoom import PinchZoomGesture
from .screenshot import ScreenshotGesture
from .close_window import CloseWindowGesture
from .pause import PauseResumeGesture
from .mute import MuteToggleGesture
from .view_tasks import TaskViewGesture

__all__ = [
    'ScrollGesture',
    'VolumeGesture',
    'PinchZoomGesture',
    'ScreenshotGesture',
    'CloseWindowGesture',
    'PauseResumeGesture',
    'MuteToggleGesture',
    'TaskViewGesture',
]
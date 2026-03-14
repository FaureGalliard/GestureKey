from __future__ import annotations
from typing import List

from domain.enums import GestureEvent
from domain.models import FrameData
from core.cooldown_manager import CooldownManager
from gestures.scroll import ScrollGesture
from gestures.volume import VolumeGesture
from gestures.zoom import PinchZoomGesture
from gestures.screenshot import ScreenshotGesture
from gestures.close_window import CloseWindowGesture
from gestures.pause import PauseResumeGesture
from gestures.mute import MuteToggleGesture
from gestures.task_view import TaskViewGesture


class GestureManager:
    def __init__(self, cooldown: CooldownManager) -> None:
        self._cooldown     = cooldown
        self._pause        = PauseResumeGesture(cooldown)
        self._mute         = MuteToggleGesture(cooldown)
        self._scroll       = ScrollGesture()
        self._volume       = VolumeGesture()
        self._zoom         = PinchZoomGesture()
        self._screenshot   = ScreenshotGesture(cooldown)
        self._close_window = CloseWindowGesture(cooldown)
        self._task_view    = TaskViewGesture(cooldown)

    def process(self, frame_data: FrameData) -> List[GestureEvent]:
        pause_events = self._pause.detect(frame_data)
        if pause_events:
            return pause_events

        mute_events = self._mute.detect(frame_data)
        if mute_events:
            return mute_events

        if self._pause.is_paused():
            return []

        events: List[GestureEvent] = []

        if frame_data.main_hand is not None:
            events.extend(self._scroll.detect(frame_data))
            events.extend(self._volume.detect(frame_data))
            events.extend(self._zoom.detect(frame_data))
            events.extend(self._screenshot.detect(frame_data))
            events.extend(self._close_window.detect(frame_data))

        events.extend(self._task_view.detect(frame_data))

        return events

    def reset_all(self) -> None:
        for gesture in [
            self._pause, self._mute, self._scroll, self._volume,
            self._zoom, self._screenshot, self._close_window, self._task_view,
        ]:
            gesture.reset()
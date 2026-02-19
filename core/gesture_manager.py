"""
GestureManager — orchestrates all gesture detectors in a clean pipeline.

Replaces the old GestureEngine which had mixed concerns and implicit coupling.

Design decisions:
  - All gestures share one CooldownManager (injected, not created here).
  - Transition gestures (pause, mute) are checked first and short-circuit.
  - Each gesture receives a FrameData value object — no positional arg soup.
  - Pause state gates all other gestures.
"""
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
    """
    The single entry point for gesture processing.

    Usage
    -----
    manager = GestureManager(cooldown)
    events  = manager.process(frame_data)

    Parameters
    ----------
    cooldown : CooldownManager
        Shared cooldown tracker injected from the outside
        (allows testing without real time).
    """

    def __init__(self, cooldown: CooldownManager) -> None:
        self._cooldown = cooldown

        # ---- transition gestures (highest priority) -------------------
        self._pause = PauseResumeGesture(cooldown)
        self._mute  = MuteToggleGesture(cooldown)

        # ---- continuous / mono-hand gestures -------------------------
        self._scroll      = ScrollGesture()
        self._volume      = VolumeGesture()
        self._zoom        = PinchZoomGesture()
        self._screenshot  = ScreenshotGesture(cooldown)
        self._close_window = CloseWindowGesture(cooldown)

        # ---- multi-hand gestures -------------------------------------
        self._task_view = TaskViewGesture(cooldown)

    # ------------------------------------------------------------------
    def process(self, frame_data: FrameData) -> List[GestureEvent]:
        """
        Process one frame and return all triggered events.

        Ordering:
        1. Pause / Resume  — highest priority, short-circuits on activation.
        2. Mute toggle     — also a transition gesture, short-circuits.
        3. All other gestures are blocked while media is paused.
        4. Mono-hand gestures.
        5. Multi-hand gestures.
        """
        # 1. Pause/Resume
        pause_events = self._pause.detect(frame_data)
        if pause_events:
            return pause_events

        # 2. Mute toggle
        mute_events = self._mute.detect(frame_data)
        if mute_events:
            return mute_events

        # 3. Gate on pause state
        if self._pause.is_paused():
            return []

        events: List[GestureEvent] = []

        # 4. Mono-hand gestures
        if frame_data.main_hand is not None:
            events.extend(self._scroll.detect(frame_data))
            events.extend(self._volume.detect(frame_data))
            events.extend(self._zoom.detect(frame_data))
            events.extend(self._screenshot.detect(frame_data))
            events.extend(self._close_window.detect(frame_data))

        # 5. Multi-hand gestures
        events.extend(self._task_view.detect(frame_data))

        return events

    def reset_all(self) -> None:
        """Force-reset every gesture detector (e.g. on hand loss)."""
        for gesture in [
            self._pause, self._mute, self._scroll, self._volume,
            self._zoom, self._screenshot, self._close_window, self._task_view,
        ]:
            gesture.reset()
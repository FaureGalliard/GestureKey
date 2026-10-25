from __future__ import annotations
from typing import Iterable, List, Optional

from gesturekey.config import GesturesConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, HandState
from gesturekey.gestures.base import Gesture, Output
from gesturekey.gestures.close_window import CloseWindowGesture
from gesturekey.gestures.grab_window import GrabWindowGesture
from gesturekey.gestures.mute import MuteToggleGesture
from gesturekey.gestures.pause import PauseResumeGesture
from gesturekey.gestures.scroll import ScrollGesture
from gesturekey.gestures.screenshot import ScreenshotGesture
from gesturekey.gestures.task_view import TaskViewGesture
from gesturekey.gestures.volume import VolumeGesture
from gesturekey.gestures.zoom import PinchZoomGesture

_LOST = (HandState.NO_HANDS, HandState.UNKNOWN)


class GestureArbiter:
    """
    Routes each frame to the gestures and decides who owns the hand.

    Order per frame:
      1. pause      — always runs, so the user can always pause/resume
      2. owner      — if a gesture is engaged, only it gets the frame
      3. mute       — runs even while paused (v2 behaviour)
      4. paused?    — stop here
      5. one-hand gestures (in priority order), then two-hand task view;
         the first one that becomes engaged claims the hand and the others
         are reset.
    """

    def __init__(self, cfg: GesturesConfig) -> None:
        cooldown = CooldownManager(default_cooldown=cfg.cooldown)
        self.pause = PauseResumeGesture(cooldown, cfg.pause)
        self._mute = MuteToggleGesture(cooldown, cfg.mute)
        self._hand_gestures: List[Gesture] = [
            g for g, enabled in (
                (GrabWindowGesture(cooldown, cfg.grab_window),   cfg.grab_window.enabled),
                (ScrollGesture(cfg.scroll),                      cfg.scroll.enabled),
                (VolumeGesture(cfg.volume),                      cfg.volume.enabled),
                (PinchZoomGesture(cfg.zoom),                     cfg.zoom.enabled),
                (ScreenshotGesture(cooldown, cfg.screenshot),    cfg.screenshot.enabled),
                (CloseWindowGesture(cooldown, cfg.close_window), cfg.close_window.enabled),
            ) if enabled
        ]
        self._two_hand: List[Gesture] = [TaskViewGesture(cooldown, cfg.task_view)] if cfg.task_view.enabled else []
        self._pause_enabled = cfg.pause.enabled
        self._mute_enabled  = cfg.mute.enabled
        self._owner: Optional[Gesture] = None

    @property
    def paused(self) -> bool:
        return self.pause.paused

    @property
    def owner(self) -> Optional[str]:
        return self._owner.NAME if self._owner else None

    def _all(self) -> Iterable[Gesture]:
        return [self.pause, self._mute, *self._hand_gestures, *self._two_hand]

    def process(self, frame: FrameData) -> Output:
        out = Output()

        if frame.state in _LOST:
            if self._owner is not None:
                self._owner.on_lost(frame.timestamp, out)
                self._release_if_done()
            return out

        if self._pause_enabled:
            self.pause.update(frame, out)
            if out.events:
                return out

        if self._owner is not None:
            self._owner.update(frame, out)
            self._release_if_done()
            return out

        if self._mute_enabled:
            self._mute.update(frame, out)
            if out.events:
                return out

        if self.paused:
            return out

        candidates = (self._hand_gestures if frame.main_hand is not None else []) + self._two_hand
        for gesture in candidates:
            gesture.update(frame, out)
            if gesture.engaged:
                self._claim(gesture)
                break
        return out

    def _claim(self, gesture: Gesture) -> None:
        self._owner = gesture
        for other in self._all():
            if other is not gesture and other is not self.pause:
                other.reset()

    def _release_if_done(self) -> None:
        if self._owner is not None and not self._owner.engaged:
            self._owner = None

    def reset_all(self) -> None:
        self._owner = None
        for gesture in self._all():
            gesture.reset()

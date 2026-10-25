from __future__ import annotations
from typing import Iterable, List, Optional

from gesturekey.config import GesturesConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, HandState
from gesturekey.gestures.base import Gesture, Output
from gesturekey.gestures.close_window import CloseWindowGesture
from gesturekey.gestures.grab_window import GrabWindowGesture
from gesturekey.gestures.mouse import MouseGesture
from gesturekey.gestures.mute import MuteToggleGesture
from gesturekey.gestures.pause import PauseResumeGesture
from gesturekey.gestures.scroll import ScrollGesture
from gesturekey.gestures.screenshot import ScreenshotGesture
from gesturekey.gestures.task_view import TaskViewGesture
from gesturekey.gestures.volume import VolumeGesture
from gesturekey.gestures.zoom import PinchZoomGesture

_LOST = (HandState.NO_HANDS,)


class GestureArbiter:
    """
    Routes each frame to the gestures and decides who owns the hand.

    Order per frame:
      1. owner  — if a gesture is engaged, only it gets the frame
      2. mute   — sequence detector, sees every state
      3. one-hand gestures (in priority order), then two-hand task view;
         the first one that becomes engaged claims the hand and the others
         are reset.

    After a gesture finishes (an owner lets go, or a one-shot fires) nothing
    new may start for `refractory` seconds: putting the hand back down passes
    through poses (palm → fist…) that would otherwise start another gesture.

    Turning GestureKey on/off (power gesture) lives in the engine, outside
    the arbiter, so it keeps working while everything here is off.
    """

    def __init__(self, cfg: GesturesConfig) -> None:
        cooldown = CooldownManager(default_cooldown=cfg.cooldown)
        self._mute = MuteToggleGesture(cooldown, cfg.mute)
        self._hand_gestures: List[Gesture] = [
            g for g, enabled in (
                (GrabWindowGesture(cooldown, cfg.grab_window),   cfg.grab_window.enabled),
                (MouseGesture(cfg.mouse, cfg.continuous),        cfg.mouse.enabled),
                (ScrollGesture(cfg.scroll, cfg.continuous),      cfg.scroll.enabled),
                (VolumeGesture(cfg.volume, cfg.continuous),      cfg.volume.enabled),
                (PinchZoomGesture(cfg.zoom, cfg.continuous),     cfg.zoom.enabled),
                (PauseResumeGesture(cooldown, cfg.pause),        cfg.pause.enabled),
                (CloseWindowGesture(cooldown, cfg.close_window), cfg.close_window.enabled),
            ) if enabled
        ]
        self._two_hand: List[Gesture] = [
            g for g, enabled in (
                (TaskViewGesture(cooldown, cfg.task_view, cfg.mouse), cfg.task_view.enabled),
                (ScreenshotGesture(cooldown, cfg.screenshot),         cfg.screenshot.enabled),
            ) if enabled
        ]
        self._mute_enabled = cfg.mute.enabled
        self._refractory = cfg.refractory
        self._quiet_until = float("-inf")
        self._owner: Optional[Gesture] = None

    @property
    def owner(self) -> Optional[Gesture]:
        return self._owner

    def _all(self) -> Iterable[Gesture]:
        return [self._mute, *self._hand_gestures, *self._two_hand]

    def process(self, frame: FrameData) -> Output:
        out = Output()

        now = frame.timestamp
        if frame.state in _LOST:
            if self._owner is not None:
                self._owner.on_lost(now, out)
                self._release_if_done(now)
            return out

        if self._owner is not None:
            self._owner.update(frame, out)   # the owner decides what an UNKNOWN frame means
            self._release_if_done(now)
            return out

        if now < self._quiet_until:
            return out
        if frame.state in (HandState.UNKNOWN, HandState.OTHER) and not frame.has_both_hands:
            return out                           # two-hand poses (the frame) often read as OTHER

        if self._mute_enabled:
            self._mute.update(frame, out)
            if out.events:
                self._quiet(now)
                return out

        one_hand = frame.main_hand is not None and frame.state not in (HandState.UNKNOWN, HandState.OTHER)
        candidates = (self._hand_gestures if one_hand else []) + self._two_hand
        for gesture in candidates:
            gesture.update(frame, out)
            if gesture.engaged:
                self._claim(gesture)
                break
        if out.events and self._owner is None:       # a one-shot fired
            self._quiet(now)
        return out

    def _quiet(self, now: float) -> None:
        self._quiet_until = now + self._refractory
        for gesture in self._all():
            gesture.reset()

    def _claim(self, gesture: Gesture) -> None:
        self._owner = gesture
        for other in self._all():
            if other is not gesture:
                other.reset()

    def _release_if_done(self, now: float) -> None:
        if self._owner is not None and not self._owner.engaged:
            self._owner = None
            self._quiet(now)

    def reset_all(self) -> None:
        self._owner = None
        for gesture in self._all():
            gesture.reset()

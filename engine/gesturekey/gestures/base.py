from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from gesturekey.actions.types import Action
from gesturekey.core.types import FrameData, GestureEvent


@dataclass
class Output:
    """What the gestures produced for one frame."""
    events:  List[GestureEvent] = field(default_factory=list)
    actions: List[Action]       = field(default_factory=list)

    def emit(self, event: GestureEvent, *actions: Action) -> None:
        self.events.append(event)
        self.actions.extend(actions)


class Gesture(ABC):
    """
    A gesture only *detects*: it reads FrameData and writes events/actions to
    `out`. It never touches the OS.

    `engaged` is True while the gesture is mid-interaction (scrolling,
    dragging…). The arbiter then routes frames only to it until it lets go.
    """

    NAME: str = "UNNAMED_GESTURE"

    @abstractmethod
    def update(self, frame: FrameData, out: Output) -> None: ...

    @abstractmethod
    def reset(self) -> None: ...

    @property
    def engaged(self) -> bool:
        return False

    def on_lost(self, now: float, out: Output) -> None:
        """Called on frames without a usable hand state (NO_HANDS / UNKNOWN)."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.NAME!r}>"

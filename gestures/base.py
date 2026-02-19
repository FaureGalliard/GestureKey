"""
Abstract base class for all gesture detectors.

Every gesture must:
  - implement detect(frame_data) → list[GestureEvent]
  - implement reset()
  - declare its NAME class attribute

This enforces a contract and enables true polymorphism in GestureManager.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from domain.enums import GestureEvent
from domain.models import FrameData


class Gesture(ABC):
    """Base class for all gesture detectors."""

    # Override in subclasses for logging / registration
    NAME: str = "UNNAMED_GESTURE"

    @abstractmethod
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        """
        Analyse one frame and return any triggered events.

        Parameters
        ----------
        frame_data : FrameData
            Encapsulates state, hand landmarks, raw landmarks and timestamp.

        Returns
        -------
        list[GestureEvent]
            Empty list when no gesture was triggered this frame.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset all internal state.
        Called by GestureManager when tracking is lost or hands change.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.NAME!r}>"
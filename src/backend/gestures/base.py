
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from domain.enums import GestureEvent
from domain.models import FrameData

class Gesture(ABC):

    # Override in subclasses for logging / registration
    NAME: str = "UNNAMED_GESTURE"

    @abstractmethod
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        """
       
        """

    @abstractmethod
    def reset(self) -> None:
        """"""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.NAME!r}>"
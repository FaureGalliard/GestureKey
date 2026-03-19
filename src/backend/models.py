from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enums import HandState

import time

Landmark2D = Tuple[float, float]
LandmarkList = List[Landmark2D]
HandsData = Dict[str, LandmarkList] 
HandsRaw = Dict[str, Any]            

@dataclass
class FrameData:
   
    state: HandState
    hands: HandsData
    hands_raw: HandsRaw = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def main_hand(self) -> Optional[LandmarkList]:
        return self.hands.get("Right") or self.hands.get("Left")

    @property
    def main_hand_raw(self) -> Optional[Any]:
        return self.hands_raw.get("Right") or self.hands_raw.get("Left")

    @property
    def has_both_hands(self) -> bool:
        return "Left" in self.hands and "Right" in self.hands
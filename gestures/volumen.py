from utils.constants import DEADZONE
from utils.utils import hand_center

class VolumeGesture:
    """Gesto de volumen con tres dedos"""
    
    def __init__(self):
        self.prev_center = None
    
    def detect(self, state, main_hand):
        """Detecta y procesa el gesto de volumen"""
        events = []
        
        if state != "THREE_FINGERS":
            self.prev_center = None
            return events
        
        center = hand_center(main_hand)
        
        if self.prev_center:
            dy = center[1] - self.prev_center[1]
            if abs(dy) > DEADZONE:
                direction = "UP" if dy < 0 else "DOWN"
                events.append(f"VOLUME_{direction}")
        
        self.prev_center = center
        return events
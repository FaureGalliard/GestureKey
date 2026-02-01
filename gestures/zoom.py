from utils.constants import DEADZONE
from utils.utils import dist

class PinchZoomGesture:
    """Gesto de zoom con pinch (pellizco)"""
    
    def __init__(self):
        self.prev_pinch_dist = None
    
    def detect(self, state, main_hand):
        """Detecta y procesa el gesto de pinch zoom"""
        events = []
        
        if state != "PINCH":
            self.prev_pinch_dist = None
            return events
        
        thumb = main_hand[4]
        index = main_hand[8]
        d = dist(thumb, index)
        
        if self.prev_pinch_dist:
            delta = d - self.prev_pinch_dist
            if abs(delta) > DEADZONE:
                events.append("ZOOM_IN" if delta > 0 else "ZOOM_OUT")
        
        self.prev_pinch_dist = d
        return events
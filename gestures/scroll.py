import time
from utils.constants import SCROLL_DEADZONE, SCROLL_TRIGGER, SCROLL_COOLDOWN
from utils.utils import hand_center

class ScrollGesture:
    """Gesto de scroll con dos dedos"""
    
    def __init__(self):
        self.scroll_accum = 0.0
        self.scroll_last_time = 0.0
        self.prev_center = None
    
    def detect(self, state, main_hand):
        """Detecta y procesa el gesto de scroll"""
        events = []
        
        if state != "TWO_FINGERS":
            self.prev_center = None
            self.scroll_accum = 0.0
            return events
        
        center = hand_center(main_hand)
        now = time.time()
        
        if self.prev_center is not None:
            dy = center[1] - self.prev_center[1]
            
            # Zona muerta
            if abs(dy) > SCROLL_DEADZONE:
                self.scroll_accum += dy
            
            # Disparo solo si se acumula suficiente movimiento
            if abs(self.scroll_accum) > SCROLL_TRIGGER:
                # Cooldown
                if now - self.scroll_last_time > SCROLL_COOLDOWN:
                    direction = "UP" if self.scroll_accum < 0 else "DOWN"
                    events.append(f"SCROLL_{direction}")
                    self.scroll_last_time = now
                    self.scroll_accum = 0.0
        
        self.prev_center = center
        return events
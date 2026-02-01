from utils.utils import hand_center

class CloseWindowGesture:
    """Gesto de cerrar ventana (puño hacia abajo)"""
    
    def __init__(self):
        self.prev_center = None
    
    def detect(self, state, main_hand, cooldown_ok_func):
        """Detecta y procesa el gesto de cerrar ventana"""
        events = []
        
        if state != "FIST":
            self.prev_center = None
            return events
        
        center = hand_center(main_hand)
        
        if self.prev_center:
            dy = center[1] - self.prev_center[1]
            if dy > 0.12 and cooldown_ok_func("CLOSE"):
                events.append("CLOSE_WINDOW")
        
        self.prev_center = center
        return events
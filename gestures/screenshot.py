from utils.utils import dist

class ScreenshotGesture:
    """Gesto de screenshot (acercar palma a la cámara)"""
    
    def __init__(self):
        self.prev_scale = None
    
    def detect(self, state, main_hand, cooldown_ok_func):
        """Detecta y procesa el gesto de screenshot"""
        events = []
        
        if state != "PALM":
            self.prev_scale = None
            return events
        
        wrist = main_hand[0]
        middle_mcp = main_hand[9]
        scale = dist(wrist, middle_mcp)
        
        if self.prev_scale:
            delta = self.prev_scale - scale
            if delta > 0.08 and cooldown_ok_func("SCREENSHOT"):
                events.append("SCREENSHOT")
        
        self.prev_scale = scale
        return events
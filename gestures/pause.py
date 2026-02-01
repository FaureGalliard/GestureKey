import time
from utils.constants import PAUSE_MIN_TIME

class PauseResumeGesture:
    """Gesto de pausa/resume (PALM -> FIST)"""
    
    def __init__(self):
        self.paused = False
    
    def detect(self, state_history, cooldown_ok_func):
        """Detecta y procesa el gesto de pausa/resume"""
        events = []
        
        if len(state_history) >= 2:
            s1, t1 = state_history[-2]
            s2, t2 = state_history[-1]
            
            if s1 == "PALM" and s2 == "FIST" and (t2 - t1) > PAUSE_MIN_TIME:
                if cooldown_ok_func("PAUSE"):
                    self.paused = not self.paused
                    events.append("PAUSE_TOGGLE")
        
        return events
    
    def is_paused(self):
        """Retorna el estado de pausa"""
        return self.paused
import time
from utils.constants import MUTE_MAX_TIME

class MuteToggleGesture:
    """Gesto de silenciar (PALM -> FIST -> PALM rápidamente)"""
    
    def detect(self, state_history, cooldown_ok_func):
        """Detecta y procesa el gesto de mute toggle"""
        events = []
        
        if len(state_history) >= 3:
            s1, t1 = state_history[-3]
            s2, t2 = state_history[-2]
            s3, t3 = state_history[-1]
            
            if (s1 == "PALM" and s2 == "FIST" and s3 == "PALM" and 
                (t3 - t1) < MUTE_MAX_TIME):
                if cooldown_ok_func("MUTE"):
                    events.append("MUTE_TOGGLE")
        
        return events
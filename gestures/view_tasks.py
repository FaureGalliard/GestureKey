from utils.utils import dist, hand_center

class TaskViewGesture:
    """Gesto de vista de tareas (juntar ambas palmas)"""
    
    def __init__(self):
        self.prev_scale = None
    
    def detect(self, state, hands, cooldown_ok_func):
        """Detecta y procesa el gesto de task view (dos manos)"""
        events = []
        
        if not ("Left" in hands and "Right" in hands):
            self.prev_scale = None
            return events
        
        if state != "PALM":
            self.prev_scale = None
            return events
        
        cL = hand_center(hands["Left"])
        cR = hand_center(hands["Right"])
        d = dist(cL, cR)
        
        if self.prev_scale:
            delta = self.prev_scale - d
            if delta > 0.1 and cooldown_ok_func("TASK_VIEW"):
                events.append("TASK_VIEW")
        
        self.prev_scale = d
        return events
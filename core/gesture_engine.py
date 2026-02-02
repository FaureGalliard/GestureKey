import time
from collections import deque
from utils.constants import COOLDOWN

# Importar todos los gestos
from gestures.scroll import ScrollGesture
from gestures.volumen import VolumeGesture
from gestures.zoom import PinchZoomGesture
from gestures.screenshot import ScreenshotGesture
from gestures.close_window import CloseWindowGesture
from gestures.pause import PauseResumeGesture
from gestures.mute import MuteToggleGesture
from gestures.view_tasks import TaskViewGesture

# =========================
# GESTURE ENGINE
# =========================

class GestureEngine:
    """Motor principal que coordina todos los gestos"""
    
    def __init__(self):
        self.last_state = None
        self.state_enter_time = time.time()
        self.last_event_time = {}
        self.state_history = deque(maxlen=10)
        
        # Inicializar todos los gestos
        self.scroll = ScrollGesture()
        self.volume = VolumeGesture()
        self.pinch_zoom = PinchZoomGesture()
        self.screenshot = ScreenshotGesture()
        self.close_window = CloseWindowGesture()
        self.pause_resume = PauseResumeGesture()
        self.mute_toggle = MuteToggleGesture()
        self.task_view = TaskViewGesture()

    def _cooldown_ok(self, name):
        """Verifica si el cooldown para un evento ha pasado"""
        t = time.time()
        last = self.last_event_time.get(name, 0)
        if t - last > COOLDOWN:
            self.last_event_time[name] = t
            return True
        return False

    def update(self, state, hands, hands_raw=None):
        """
        Actualiza el motor de gestos con el estado actual
        
        Parámetros:
        - state: Estado predicho de la mano
        - hands: Diccionario con landmarks normalizados
        - hands_raw: Diccionario con objetos raw de MediaPipe (para profundidad)
        """
        now = time.time()
        events = []

        # ---------------------
        # HISTORIAL DE ESTADOS
        # ---------------------
        if state != self.last_state:
            self.state_enter_time = now
            self.last_state = state

        self.state_history.append((state, now))

        # ---------------------
        # GESTOS DE TRANSICIÓN
        # ---------------------
        
        # Pausa/Resume
        pause_events = self.pause_resume.detect(self.state_history, self._cooldown_ok)
        if pause_events:
            return pause_events
        
        # Mute Toggle
        mute_events = self.mute_toggle.detect(self.state_history, self._cooldown_ok)
        if mute_events:
            return mute_events

        # Si está pausado, no procesar más gestos
        if self.pause_resume.is_paused():
            return events

        # ---------------------
        # GESTOS MONO-MANO
        # ---------------------
        main_hand = hands.get("Right") or hands.get("Left")
        main_hand_raw = None
        
        # Obtener el hand_landmarks raw correspondiente
        if hands_raw is not None:
            main_hand_raw = hands_raw.get("Right") or hands_raw.get("Left")
        
        if main_hand:
            # Scroll (con datos raw para profundidad)
            events.extend(self.scroll.detect(state, main_hand, main_hand_raw))
            
            # Volume
            events.extend(self.volume.detect(state, main_hand))
            
            # Pinch Zoom
            events.extend(self.pinch_zoom.detect(state, main_hand))
            
            # Screenshot
            events.extend(self.screenshot.detect(state, main_hand, self._cooldown_ok))
            
            # Close Window
            events.extend(self.close_window.detect(state, main_hand, self._cooldown_ok))

        # ---------------------
        # GESTOS MULTI-MANO
        # ---------------------
        events.extend(self.task_view.detect(state, hands, self._cooldown_ok))

        return events
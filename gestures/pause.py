import time
import win32api
import win32con
from utils.constants import PAUSE_MIN_TIME, PAUSE_MAX_TIME, PAUSE_COOLDOWN

class PauseResumeGesture:
    """
    Gesto de pausa/resume con detección robusta de transición PALM -> FIST
    
    Características:
    - Validación temporal de transición
    - Protección contra falsos positivos
    - Cooldown configurable
    - Feedback de estado
    """
    
    def __init__(self):
        self.paused = False
        
        # Estado de la transición
        self.palm_start_time = None
        self.transition_armed = False
        self.last_state = None
        
        # Cooldown personalizado (override del global si es necesario)
        self.last_toggle_time = 0
        
        # Historial para validación
        self.state_buffer = []
        self.buffer_size = 5  # frames para validar estabilidad
        
    def detect(self, state_history, cooldown_ok_func):
        """
        Detecta y procesa el gesto de pausa/resume
        
        Parámetros:
        - state_history: deque con tuplas (estado, timestamp)
        - cooldown_ok_func: función para verificar cooldown global
        
        Retorna:
        - Lista de eventos generados
        """
        events = []
        
        if len(state_history) < 2:
            return events
        
        current_state, current_time = state_history[-1]
        
        # =====================
        # MÁQUINA DE ESTADOS
        # =====================
        
        # 1️⃣ DETECTAR INICIO DE PALM ESTABLE
        if current_state == "PALM":
            if self.last_state != "PALM":
                # Transición a PALM - iniciar cronómetro
                self.palm_start_time = current_time
                self.transition_armed = False
                print(f"[PAUSE] 🟢 PALM detectado - esperando estabilidad")
            
            elif self.palm_start_time is not None:
                # PALM estable - verificar tiempo mínimo
                hold_time = current_time - self.palm_start_time
                
                if hold_time >= PAUSE_MIN_TIME and not self.transition_armed:
                    # PALM confirmado - listo para detectar FIST
                    self.transition_armed = True
                    print(f"[PAUSE] ✅ PALM armado ({hold_time*1000:.0f}ms)")
        
        # 2️⃣ DETECTAR TRANSICIÓN A FIST
        elif current_state == "FIST":
            if self.transition_armed and self.last_state == "PALM":
                # ¡Transición válida detectada!
                transition_time = current_time - self.palm_start_time
                
                # Validar ventana temporal (no debe ser demasiado lento)
                if hasattr(self, 'PAUSE_MAX_TIME') and transition_time > PAUSE_MAX_TIME:
                    print(f"[PAUSE] ⚠️ Transición muy lenta ({transition_time*1000:.0f}ms)")
                    self._reset()
                    self.last_state = current_state
                    return events
                
                # Verificar cooldown
                if self._cooldown_ok(cooldown_ok_func):
                    # ✅ EJECUTAR ACCIÓN
                    self._execute_toggle()
                    
                    self.paused = not self.paused
                    action = "PAUSED" if self.paused else "RESUMED"
                    
                    print(f"[PAUSE] 🎬 Media {action} (transición: {transition_time*1000:.0f}ms)")
                    events.append(f"PAUSE_TOGGLE_{action}")
                    
                    self._reset()
                else:
                    print(f"[PAUSE] 🔒 Cooldown activo")
            
            # Reset si FIST sin armado previo
            elif not self.transition_armed:
                self._reset()
        
        # 3️⃣ OTROS ESTADOS - RESET
        else:
            if self.transition_armed:
                print(f"[PAUSE] ❌ Transición interrumpida por {current_state}")
            self._reset()
        
        self.last_state = current_state
        return events
    
    def _execute_toggle(self):
        """Ejecuta el comando de media play/pause"""
        try:
            # Presionar tecla
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            time.sleep(0.05)  # pequeña pausa entre press y release
            # Soltar tecla
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
            
        except Exception as e:
            print(f"[PAUSE] ⚠️ Error ejecutando comando: {e}")
    
    def _cooldown_ok(self, cooldown_ok_func):
        """
        Verifica cooldown con doble verificación
        - Usa el cooldown global del engine
        - Además mantiene su propio cooldown local
        """
        now = time.time()
        
        # Cooldown local (opcional, más restrictivo)
        if hasattr(self, 'PAUSE_COOLDOWN'):
            if now - self.last_toggle_time < PAUSE_COOLDOWN:
                return False
        
        # Cooldown global
        if cooldown_ok_func("PAUSE"):
            self.last_toggle_time = now
            return True
        
        return False
    
    def _reset(self):
        """Resetea el estado de detección"""
        self.palm_start_time = None
        self.transition_armed = False
    
    def is_paused(self):
        """Retorna el estado de pausa actual"""
        return self.paused
    
    def get_status(self):
        """Retorna información de debug del estado actual"""
        return {
            'paused': self.paused,
            'armed': self.transition_armed,
            'palm_time': time.time() - self.palm_start_time if self.palm_start_time else None
        }
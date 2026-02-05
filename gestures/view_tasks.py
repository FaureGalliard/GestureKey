import time
import pyautogui
from utils.constants import (
    TASK_VIEW_ARM_TIME,
    TASK_VIEW_MIN_APPROACH,
    TASK_VIEW_COOLDOWN
)
from utils.utils import hand_center, dist


# =====================
# TUNING (IMPORTANTE)
# =====================
MIN_INITIAL_DISTANCE = 0.3      # distancia mínima inicial entre manos (30% de pantalla)
MIN_APPROACH_TOTAL = 0.15       # acercamiento total mínimo para activar (15% de pantalla)
MAX_APPROACH_SPEED = 0.5        # velocidad máxima de acercamiento por frame (evita falsos positivos)

# 🛡️ PROTECCIÓN CONTRA ERRORES DE DETECCIÓN (solo pre-armado)
MAX_POSITION_JUMP = 0.2         # salto máximo permitido entre frames
OUTLIER_RECOVERY_FRAMES = 2     # frames para recuperarse de un outlier

# 🎯 SUAVIZADO (solo para validación, no para distancia)
DISTANCE_ALPHA = 0.6            # suavizado exponencial de distancia entre manos

# 🥉 DETECCIÓN DE ESTABILIDAD
STABILITY_TIME = 0.15           # tiempo mínimo con ambas manos detectadas antes de armar
STABILITY_FRAMES = 3            # frames consecutivos necesarios para validar detección


class TaskViewGesture:
    """
    Gesto de Task View (Win+Tab) - juntar ambas palmas
    
    Características:
    - Requiere dos manos en estado PALM
    - Validación temporal de estabilidad
    - Protección contra falsos positivos
    - Cooldown configurable
    """
    
    def __init__(self):
        # Estado de detección
        self.both_hands_start_time = None
        self.gesture_armed = False
        
        # Referencia inicial
        self.initial_distance = None
        self.anchor_distance = None
        
        # Distancia anterior para calcular acercamiento
        self.prev_distance_raw = None
        
        # 🛡️ protección contra outliers (solo pre-armado)
        self.outlier_count = 0
        self.last_valid_left = None
        self.last_valid_right = None
        self.last_valid_distance = None
        
        # 🎯 suavizado de distancia (solo para validación)
        self.smoothed_distance = None
        
        # 🥉 detección de estabilidad
        self.stable_detection_count = 0
        
        # Acumulador de acercamiento
        self.total_approach = 0.0
        
        # Cooldown
        self.last_activation_time = 0
        
        pyautogui.PAUSE = 0.01
    
    # =====================
    # MAIN
    # =====================
    def detect(self, state, hands, cooldown_ok_func):
        """
        Detecta y procesa el gesto de task view (dos manos)
        
        Parámetros:
        - state: Estado actual de las manos
        - hands: Diccionario con landmarks normalizados {"Left": [...], "Right": [...]}
        - cooldown_ok_func: Función para verificar cooldown global
        
        Retorna:
        - Lista de eventos generados
        """
        events = []
        now = time.time()
        
        # ---- verificar que hay dos manos
        if not ("Left" in hands and "Right" in hands):
            self._reset()
            return events
        
        # ---- verificar estado correcto (PALM)
        if state != "PALM":
            self._reset()
            return events
        
        # ---- calcular centros y distancia
        center_left = hand_center(hands["Left"])
        center_right = hand_center(hands["Right"])
        distance_raw = dist(center_left, center_right)
        
        # 🎯 suavizar distancia solo para validación
        if self.smoothed_distance is None:
            self.smoothed_distance = distance_raw
        else:
            self.smoothed_distance = DISTANCE_ALPHA * distance_raw + (1 - DISTANCE_ALPHA) * self.smoothed_distance
        
        # ---- debug
        print(
            f"[TASK_VIEW] "
            f"DIST={distance_raw:.3f} "
            f"SMOOTH={self.smoothed_distance:.3f} "
            f"APPROACH={self.total_approach:.3f} "
            f"STABLE={self.stable_detection_count} "
            f"ARMED={self.gesture_armed}"
        )
        
        # ========================
        # 🥉 VALIDACIÓN DE ESTABILIDAD
        # ========================
        if not self.gesture_armed:
            # validar que la detección sea estable
            is_stable = self._validate_stability(center_left, center_right, distance_raw)
            
            if is_stable:
                self.stable_detection_count += 1
                self.last_valid_left = center_left
                self.last_valid_right = center_right
                self.last_valid_distance = self.smoothed_distance
            else:
                # detección inestable
                self.stable_detection_count = 0
                self.outlier_count += 1
                
                if self.outlier_count > OUTLIER_RECOVERY_FRAMES:
                    print("[TASK_VIEW] ⚠️ Demasiados outliers - reseteando")
                    self._reset()
                
                return events
            
            # resetear contador de outliers si la detección es estable
            self.outlier_count = 0
            
            # necesitamos suficientes frames estables antes de continuar
            if self.stable_detection_count < STABILITY_FRAMES:
                return events
        
        # ========================
        # ARMADO POR TIEMPO
        # ========================
        if not self.gesture_armed:
            # primera detección estable
            if self.both_hands_start_time is None:
                self.both_hands_start_time = now
                self.initial_distance = distance_raw
                self.anchor_distance = distance_raw
                self.prev_distance_raw = distance_raw
                print(f"[TASK_VIEW] 🟢 Ambas manos detectadas - distancia inicial: {distance_raw:.3f}")
                return events
            
            # verificar que la distancia inicial sea suficiente
            if self.initial_distance < MIN_INITIAL_DISTANCE:
                print(f"[TASK_VIEW] ⚠️ Manos muy juntas al inicio ({self.initial_distance:.3f})")
                self._reset()
                return events
            
            # esperar tiempo de estabilidad
            if now - self.both_hands_start_time < STABILITY_TIME:
                self.prev_distance_raw = distance_raw
                return events
            
            # armar el gesto
            self.gesture_armed = True
            print(f"[TASK_VIEW] ✅ Gesto armado - esperando acercamiento")
        
        # ========================
        # DETECCIÓN DE ACERCAMIENTO
        # ========================
        if self.prev_distance_raw is not None:
            # 👉 usar distancia CRUDA para delta, no suavizada
            delta = self.prev_distance_raw - distance_raw
            
            # validar que el acercamiento no sea demasiado rápido (outlier)
            if delta > MAX_APPROACH_SPEED:
                print(f"[TASK_VIEW] ⚠️ Acercamiento muy rápido: {delta:.3f}")
                self.prev_distance_raw = distance_raw
                return events
            
            # solo acumular si hay acercamiento (delta > 0)
            if delta > 0:
                self.total_approach += delta
                print(f"[TASK_VIEW] 📏 Acercamiento: +{delta:.3f} (total: {self.total_approach:.3f})")
            
            # verificar si se alcanzó el umbral de acercamiento
            if self.total_approach >= MIN_APPROACH_TOTAL:
                # verificar cooldown
                if self._cooldown_ok(cooldown_ok_func):
                    # ✅ EJECUTAR ACCIÓN
                    self._execute_task_view()
                    
                    print(f"[TASK_VIEW] 🎬 Task View activado (acercamiento total: {self.total_approach:.3f})")
                    events.append("TASK_VIEW")
                    
                    self._reset()
                else:
                    print(f"[TASK_VIEW] 🔒 Cooldown activo")
        
        self.prev_distance_raw = distance_raw
        return events
    
    # =====================
    # VALIDACIÓN
    # =====================
    def _validate_stability(self, center_left, center_right, distance):
        """
        Valida que la detección de ambas manos sea consistente.
        Retorna False si detecta un outlier.
        """
        # primera detección siempre es válida
        if self.last_valid_left is None or self.last_valid_right is None:
            return True
        
        # validar salto de posición de mano izquierda
        left_jump = dist(center_left, self.last_valid_left)
        if left_jump > MAX_POSITION_JUMP:
            print(f"[TASK_VIEW] ⚠️ Salto de mano izquierda: {left_jump:.3f}")
            return False
        
        # validar salto de posición de mano derecha
        right_jump = dist(center_right, self.last_valid_right)
        if right_jump > MAX_POSITION_JUMP:
            print(f"[TASK_VIEW] ⚠️ Salto de mano derecha: {right_jump:.3f}")
            return False
        
        return True
    
    # =====================
    # HELPERS
    # =====================
    def _execute_task_view(self):
        """Ejecuta el comando Win+Tab para abrir Task View"""
        try:
            # Presionar Win+Tab
            pyautogui.hotkey('win', 'tab')
            
        except Exception as e:
            print(f"[TASK_VIEW] ⚠️ Error ejecutando comando: {e}")
    
    def _cooldown_ok(self, cooldown_ok_func):
        """
        Verifica cooldown con doble verificación
        - Usa el cooldown global del engine
        - Además mantiene su propio cooldown local
        """
        now = time.time()
        
        # Cooldown local
        if now - self.last_activation_time < TASK_VIEW_COOLDOWN:
            return False
        
        # Cooldown global
        if cooldown_ok_func("TASK_VIEW"):
            self.last_activation_time = now
            return True
        
        return False
    
    def _reset(self):
        """Resetea el estado de detección"""
        self.both_hands_start_time = None
        self.gesture_armed = False
        self.initial_distance = None
        self.anchor_distance = None
        self.prev_distance_raw = None
        self.smoothed_distance = None
        self.stable_detection_count = 0
        self.outlier_count = 0
        self.last_valid_left = None
        self.last_valid_right = None
        self.last_valid_distance = None
        self.total_approach = 0.0
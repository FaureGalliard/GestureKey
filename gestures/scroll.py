import time
import pyautogui
from utils.constants import (
    SCROLL_DEADZONE,
    SCROLL_ARM_TIME,
    SCROLL_MAX_TIME,
    INTENT_Z_ENTER,
    INTENT_Z_EXIT
)
from utils.utils import hand_center


# =====================
# TUNING (IMPORTANTE)
# =====================
BASE_GAIN = 10000          # ganancia mínima
ACCEL_FACTOR = 15000       # cuánto acelera al alejarte del punto inicial
MAX_SCROLL_STEP = 1400     # límite de seguridad
MIN_SCROLL_STEP = 10       # evita micro-scroll

# 🎯 COMPENSACIÓN DE DISTANCIA
DISTANCE_MULTIPLIER = 2.5  # cuánto amplificar cuando estás lejos
REFERENCE_DISTANCE = 0.15  # distancia de referencia (z típico cercano)

# 🎯 NORMALIZACIÓN POR TAMAÑO DE MANO
REFERENCE_HAND_SIZE = 0.15  # tamaño típico de mano cercana (distancia muñeca-dedo medio)
SIZE_COMPENSATION = True     # activar normalización por tamaño


class ScrollGesture:
    """Scroll tipo touchpad con aceleración progresiva y compensación de distancia"""

    def __init__(self):
        self.prev_center = None

        self.scroll_start_time = None
        self.scroll_active = False

        self.intent_active = False

        # referencia para aceleración
        self.anchor_y = None
        
        # 🎯 tamaño de mano para normalización
        self.hand_size = None

        pyautogui.PAUSE = 0.01

    # =====================
    # MAIN
    # =====================
    def detect(self, state, main_hand, hand_landmarks_raw=None):
        events = []
        now = time.time()

        # ---- estado correcto
        if state != "TWO_FINGERS":
            self._reset()
            return events

        center = hand_center(main_hand)

        # 🔧 calcular profundidad absoluta (z de muñeca)
        distance_z = None
        current_hand_size = None
        if hand_landmarks_raw is not None:
            distance_z = abs(hand_landmarks_raw.landmark[0].z)
            # calcular tamaño de mano (distancia muñeca -> dedo medio tip)
            current_hand_size = self._calculate_hand_size(hand_landmarks_raw)

        # ---- debug
        if hand_landmarks_raw is not None:
            depth = self._relative_depth(hand_landmarks_raw)
            print(
                f"Y={center[1]:.3f} "
                f"DEPTH={depth:.4f} "
                f"DIST_Z={distance_z:.4f} "
                f"HAND_SIZE={current_hand_size:.4f} "
                f"INTENT={self.intent_active} "
                f"ARMED={self.scroll_active}"
            )

        # ---- intención por profundidad
        if hand_landmarks_raw is not None:
            if not self.depth_intent_ok(hand_landmarks_raw):
                self._reset()
                return events

        # ---- armado por tiempo
        if not self.scroll_active:
            if self.scroll_start_time is None:
                self.scroll_start_time = now
                self.prev_center = center
                self.anchor_y = center[1]   # 🎯 punto inicial
                self.hand_size = current_hand_size  # 🎯 tamaño de referencia
                return events

            if now - self.scroll_start_time < SCROLL_ARM_TIME:
                self.prev_center = center
                return events

            self.scroll_active = True

        # ---- timeout máximo
        if now - self.scroll_start_time > SCROLL_MAX_TIME:
            self._reset()
            return events

        # =====================
        # SCROLL PROPORCIONAL + ACELERADO + COMPENSADO POR DISTANCIA + TAMAÑO
        # =====================
        if self.prev_center is not None:
            dy = center[1] - self.prev_center[1]
            
            # 🎯 normalizar dy por cambio de tamaño de mano
            if SIZE_COMPENSATION and current_hand_size is not None and self.hand_size is not None and self.hand_size > 0:
                # si la mano es más pequeña (lejos), el mismo dy físico debe generar más scroll
                size_ratio = self.hand_size / current_hand_size
                dy_normalized = dy * size_ratio
            else:
                dy_normalized = dy

            if abs(dy_normalized) > SCROLL_DEADZONE:
                # 🎯 compensación por distancia
                distance_factor = 1.0
                if distance_z is not None:
                    # cuanto más lejos (mayor z), mayor el factor
                    distance_factor = 1.0 + (distance_z / REFERENCE_DISTANCE - 1.0) * DISTANCE_MULTIPLIER
                    distance_factor = max(0.5, min(5.0, distance_factor))  # clamp seguro

                # distancia desde el punto inicial
                dist_from_anchor = abs(center[1] - self.anchor_y)

                # ganancia dinámica con compensación
                gain = (BASE_GAIN + dist_from_anchor * ACCEL_FACTOR) * distance_factor

                scroll_amount = int(dy_normalized * gain)

                # clamp
                if abs(scroll_amount) >= MIN_SCROLL_STEP:
                    scroll_amount = max(
                        -MAX_SCROLL_STEP,
                        min(MAX_SCROLL_STEP, scroll_amount)
                    )

                    # invertir signo para scroll natural
                    pyautogui.scroll(-scroll_amount)
                    events.append("SCROLL")

        self.prev_center = center
        return events

    # =====================
    # HELPERS
    # =====================
    def _calculate_hand_size(self, hand_landmarks_raw):
        """Calcula el tamaño de la mano (distancia muñeca -> punta dedo medio)"""
        wrist = hand_landmarks_raw.landmark[0]
        middle_tip = hand_landmarks_raw.landmark[12]
        
        # distancia euclidiana en espacio 3D
        dx = middle_tip.x - wrist.x
        dy = middle_tip.y - wrist.y
        dz = middle_tip.z - wrist.z
        
        return (dx**2 + dy**2 + dz**2) ** 0.5
    
    def depth_intent_ok(self, hand_landmarks_raw):
        depth = self._relative_depth(hand_landmarks_raw)

        if not self.intent_active:
            if depth < INTENT_Z_ENTER:
                self.intent_active = True
        else:
            if depth > INTENT_Z_EXIT:
                self.intent_active = False

        return self.intent_active

    def _relative_depth(self, hand_landmarks_raw):
        wrist_z = hand_landmarks_raw.landmark[0].z
        tip_ids = [4, 8, 12, 16, 20]
        tip_z = sum(hand_landmarks_raw.landmark[i].z for i in tip_ids) / len(tip_ids)
        return tip_z - wrist_z

    def _reset(self):
        self.prev_center = None
        self.scroll_active = False
        self.scroll_start_time = None
        self.anchor_y = None
        self.hand_size = None
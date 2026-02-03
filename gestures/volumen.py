import time
import pyautogui
from utils.constants import (
    VOLUME_DEADZONE,
    VOLUME_ARM_TIME,
    VOLUME_MAX_TIME,
    INTENT_Z_ENTER,
    INTENT_Z_EXIT
)
from utils.utils import hand_center


# =====================
# TUNING (IMPORTANTE)
# =====================
BASE_GAIN = 100            # ganancia mínima (menor que scroll, volumen es más sensible)
ACCEL_FACTOR = 200        # cuánto acelera al alejarte del punto inicial
MAX_VOLUME_STEP = 30        # límite de seguridad (steps de volumen)
MIN_VOLUME_STEP = 1        # mínimo cambio perceptible

# 🎯 COMPENSACIÓN DE DISTANCIA
DISTANCE_MULTIPLIER = 2.3  # cuánto amplificar cuando estás lejos
REFERENCE_DISTANCE = 0.15  # distancia de referencia (z típico cercano)

# 🎯 NORMALIZACIÓN POR TAMAÑO DE MANO
REFERENCE_HAND_SIZE = 0.15  # tamaño típico de mano cercana (distancia muñeca-dedo medio)
SIZE_COMPENSATION = True    # activar normalización por tamaño


class VolumeGesture:
    """Control de volumen tipo touchpad con aceleración progresiva y compensación de distancia"""

    def __init__(self):
        self.prev_center = None

        self.volume_start_time = None
        self.volume_active = False

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
        if state != "THREE_FINGERS":
            self._reset()
            return events

        center = hand_center(main_hand)

        # 🔧 calcular profundidad absoluta (z de muñeca) y tamaño de mano
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
                f"[VOL] Y={center[1]:.3f} "
                f"DEPTH={depth:.4f} "
                f"DIST_Z={distance_z:.4f} "
                f"HAND_SIZE={current_hand_size:.4f} "
                f"INTENT={self.intent_active} "
                f"ARMED={self.volume_active}"
            )

        # ---- intención por profundidad
        if hand_landmarks_raw is not None:
            if not self.depth_intent_ok(hand_landmarks_raw):
                self._reset()
                return events

        # ---- armado por tiempo
        if not self.volume_active:
            if self.volume_start_time is None:
                self.volume_start_time = now
                self.prev_center = center
                self.anchor_y = center[1]   # 🎯 punto inicial
                self.hand_size = current_hand_size  # 🎯 tamaño de referencia
                return events

            if now - self.volume_start_time < VOLUME_ARM_TIME:
                self.prev_center = center
                return events

            self.volume_active = True

        # ---- timeout máximo
        if now - self.volume_start_time > VOLUME_MAX_TIME:
            self._reset()
            return events

        # =====================
        # VOLUMEN PROPORCIONAL + ACELERADO + COMPENSADO POR DISTANCIA + TAMAÑO
        # =====================
        if self.prev_center is not None:
            dy = center[1] - self.prev_center[1]
            
            # 🎯 normalizar dy por cambio de tamaño de mano
            if SIZE_COMPENSATION and current_hand_size is not None and self.hand_size is not None and self.hand_size > 0:
                # si la mano es más pequeña (lejos), el mismo dy físico debe generar más cambio
                size_ratio = self.hand_size / current_hand_size
                dy_normalized = dy * size_ratio
            else:
                dy_normalized = dy

            if abs(dy_normalized) > VOLUME_DEADZONE:
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

                volume_steps = int(dy_normalized * gain)

                # clamp
                if abs(volume_steps) >= MIN_VOLUME_STEP:
                    volume_steps = max(
                        -MAX_VOLUME_STEP,
                        min(MAX_VOLUME_STEP, volume_steps)
                    )

                    # mano arriba (dy negativo) = subir volumen
                    # mano abajo (dy positivo) = bajar volumen
                    if dy_normalized < 0:
                        # subir volumen
                        for _ in range(abs(volume_steps)):
                            pyautogui.press('volumeup')
                        events.append("VOLUME_UP")
                    else:
                        # bajar volumen
                        for _ in range(abs(volume_steps)):
                            pyautogui.press('volumedown')
                        events.append("VOLUME_DOWN")

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
        self.volume_active = False
        self.volume_start_time = None
        self.anchor_y = None
        self.hand_size = None
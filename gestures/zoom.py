import time
import pyautogui
from utils.constants import (
    ZOOM_ARM_TIME,
    INTENT_Z_ENTER,
    INTENT_Z_EXIT
)
from utils.utils import hand_center


# =====================
# TUNING (IMPORTANTE)
# =====================
BASE_GAIN = 10            # ganancia mínima
ACCEL_FACTOR = 1.5         # cuánto acelera al alejarte del punto inicial
MAX_ZOOM_STEP = 5         # límite de seguridad (steps de zoom)
MIN_ZOOM_STEP = 1          # mínimo cambio perceptible

# 🎯 NORMALIZACIÓN POR TAMAÑO DE MANO
REFERENCE_HAND_SIZE = 0.15  # tamaño típico de mano cercana
SIZE_COMPENSATION = True    # activar normalización por tamaño
SIZE_RATIO_MIN = 0.3        # clamp inferior
SIZE_RATIO_MAX = 1.8        # clamp superior

# 🛡️ PROTECCIÓN CONTRA ERRORES DE DETECCIÓN (solo pre-armado)
MAX_POSITION_JUMP = 0.15    # salto máximo permitido entre frames
MAX_SIZE_CHANGE = 0.3       # cambio máximo de tamaño de mano
MAX_PINCH_JUMP = 0.1        # salto máximo de distancia pinch (10% de pantalla)
OUTLIER_RECOVERY_FRAMES = 2 # frames para recuperarse de un outlier

# 🎯 SUAVIZADO (solo para validación, no para d_pinch)
POSITION_ALPHA = 0.7        # suavizado exponencial de posición
SIZE_ALPHA = 0.6            # suavizado del tamaño de mano
PINCH_ALPHA = 0.5           # suavizado de distancia pinch (para validación)

# 🥇 DEADZONE DE VELOCIDAD (mata micro-movimientos)
VELOCITY_DEADZONE = 0.003   # umbral de velocidad mínima para zoom

# 🥈 INTEGRADOR TEMPORAL (suaviza dirección)
TEMPORAL_INTEGRATION_FRAMES = 3  # frames a acumular antes de zoom
D_BUFFER_SIZE = 3                # tamaño del buffer

# 🥉 DETECCIÓN DE QUIETUD (pinch quieto = no zoom)
MOTION_THRESHOLD = 0.004    # movimiento mínimo para considerar "en movimiento"
STILLNESS_TIMEOUT = 0.1     # 100ms sin movimiento = quieto


class PinchZoomGesture:
    """Zoom robusto con pinch (pellizco) y protección contra errores de detección"""

    def __init__(self):
        self.prev_pinch_dist_raw = None   # distancia cruda para calcular delta
        self.zoom_start_time = None
        self.zoom_active = False
        self.intent_active = False

        # referencia para aceleración
        self.anchor_pinch_dist = None
        
        # 🎯 tamaño de mano para normalización (suavizado)
        self.hand_size = None
        self.smoothed_hand_size = None
        
        # 🛡️ protección contra outliers (solo pre-armado)
        self.outlier_count = 0
        self.last_valid_center = None
        self.last_valid_size = None
        self.last_valid_pinch = None
        
        # 🎯 suavizado (solo para validación)
        self.smoothed_center = None
        self.smoothed_pinch_dist = None
        
        # 🥈 integrador temporal - buffer de delta
        self.d_buffer = []
        
        # 🥉 detección de quietud
        self.last_motion_time = None
        self.pinch_100ms_ago = None
        self.time_100ms_ago = None

        pyautogui.PAUSE = 0.01

    # =====================
    # MAIN
    # =====================
    def detect(self, state, main_hand, hand_landmarks_raw=None):
        events = []
        now = time.time()

        # ---- estado correcto
        if state != "PINCH":
            self._reset()
            return events

        center_raw = hand_center(main_hand)
        
        # calcular distancia pinch (thumb-index)
        thumb = main_hand[4]
        index = main_hand[8]
        pinch_dist_raw = self._euclidean_dist(thumb, index)

        # 🔧 calcular profundidad absoluta (z de muñeca) y tamaño de mano
        distance_z = None
        current_hand_size = None
        if hand_landmarks_raw is not None:
            distance_z = abs(hand_landmarks_raw.landmark[0].z)
            current_hand_size = self._calculate_hand_size(hand_landmarks_raw)

        # 🎯 suavizar tamaño de mano para reducir ruido
        if self.smoothed_hand_size is None:
            self.smoothed_hand_size = current_hand_size
        else:
            if current_hand_size is not None:
                self.smoothed_hand_size = SIZE_ALPHA * current_hand_size + (1 - SIZE_ALPHA) * self.smoothed_hand_size

        # 🎯 suavizar posición solo para validación
        if self.smoothed_center is None:
            self.smoothed_center = center_raw
        else:
            self.smoothed_center = (
                POSITION_ALPHA * center_raw[0] + (1 - POSITION_ALPHA) * self.smoothed_center[0],
                POSITION_ALPHA * center_raw[1] + (1 - POSITION_ALPHA) * self.smoothed_center[1]
            )
        
        # 🎯 suavizar distancia pinch solo para validación
        if self.smoothed_pinch_dist is None:
            self.smoothed_pinch_dist = pinch_dist_raw
        else:
            self.smoothed_pinch_dist = PINCH_ALPHA * pinch_dist_raw + (1 - PINCH_ALPHA) * self.smoothed_pinch_dist

        # ---- debug
        if hand_landmarks_raw is not None:
            depth = self._relative_depth(hand_landmarks_raw)
            print(
                f"[ZOOM] PINCH={pinch_dist_raw:.3f} "
                f"DEPTH={depth:.4f} "
                f"DIST_Z={distance_z:.4f} "
                f"SIZE={current_hand_size:.4f} "
                f"SIZE_SMOOTH={self.smoothed_hand_size:.4f} "
                f"OUTLIERS={self.outlier_count} "
                f"INTENT={self.intent_active} "
                f"ARMED={self.zoom_active}"
            )

        # 🛡️ VALIDACIÓN DE OUTLIERS - SOLO PRE-ARMADO
        if not self.zoom_active:
            is_valid_detection = self._validate_detection(
                self.smoothed_center, 
                self.smoothed_hand_size,
                self.smoothed_pinch_dist
            )
            
            if not is_valid_detection:
                self.outlier_count += 1
                if self.outlier_count > OUTLIER_RECOVERY_FRAMES:
                    print("[ZOOM] ⚠️ Demasiados outliers pre-armado - reseteando")
                    self._reset()
                return events
            else:
                self.outlier_count = 0
                self.last_valid_center = self.smoothed_center
                self.last_valid_size = self.smoothed_hand_size
                self.last_valid_pinch = self.smoothed_pinch_dist

        # ---- intención por profundidad
        if hand_landmarks_raw is not None:
            if not self.depth_intent_ok(hand_landmarks_raw):
                self._reset()
                return events

        # ---- armado por tiempo
        if not self.zoom_active:
            if self.zoom_start_time is None:
                self.zoom_start_time = now
                self.prev_pinch_dist_raw = pinch_dist_raw
                self.anchor_pinch_dist = pinch_dist_raw  # 🎯 punto inicial
                self.hand_size = self.smoothed_hand_size
                return events

            if now - self.zoom_start_time < ZOOM_ARM_TIME:
                self.prev_pinch_dist_raw = pinch_dist_raw
                return events

            self.zoom_active = True
            print("[ZOOM] ✅ Armado y activo")

        # =====================
        # ZOOM CON DELTA CRUDO (sin suavizado)
        # =====================
        if self.prev_pinch_dist_raw is not None:
            # 👉 usar distancia CRUDA para delta, no suavizada
            delta_raw = pinch_dist_raw - self.prev_pinch_dist_raw
            
            # 🎯 normalizar delta por cambio de tamaño de mano
            if SIZE_COMPENSATION and self.smoothed_hand_size is not None and self.hand_size is not None and self.hand_size > 0:
                size_ratio = self.hand_size / self.smoothed_hand_size
                size_ratio = max(SIZE_RATIO_MIN, min(SIZE_RATIO_MAX, size_ratio))
                delta_normalized = delta_raw * size_ratio
            else:
                delta_normalized = delta_raw

            # 🥇 DEADZONE DE VELOCIDAD - mata micro-movimientos
            if abs(delta_normalized) < VELOCITY_DEADZONE:
                delta_normalized = 0.0
            
            # 🥉 DETECCIÓN DE QUIETUD - actualizar estado de movimiento
            if abs(delta_normalized) > MOTION_THRESHOLD:
                self.last_motion_time = now
            else:
                if self.last_motion_time and now - self.last_motion_time > STILLNESS_TIMEOUT:
                    # pinch quieto por >100ms → no zoom
                    self.prev_pinch_dist_raw = pinch_dist_raw
                    return events
            
            # 🥉 DETECCIÓN DE QUIETUD - verificar desplazamiento total en 100ms
            if self.pinch_100ms_ago is None or self.time_100ms_ago is None:
                self.pinch_100ms_ago = pinch_dist_raw
                self.time_100ms_ago = now
            elif now - self.time_100ms_ago >= 0.1:
                total_displacement = abs(pinch_dist_raw - self.pinch_100ms_ago)
                if total_displacement < MOTION_THRESHOLD:
                    # pinch prácticamente quieto → no zoom
                    self.prev_pinch_dist_raw = pinch_dist_raw
                    return events
                self.pinch_100ms_ago = pinch_dist_raw
                self.time_100ms_ago = now
            
            # 🥈 INTEGRADOR TEMPORAL - acumular delta en buffer
            if delta_normalized != 0.0:
                self.d_buffer.append(delta_normalized)
                if len(self.d_buffer) > D_BUFFER_SIZE:
                    self.d_buffer.pop(0)
            
            # esperar a tener suficientes muestras
            if len(self.d_buffer) < TEMPORAL_INTEGRATION_FRAMES:
                self.prev_pinch_dist_raw = pinch_dist_raw
                return events
            
            # 👉 usar promedio del buffer para suavizar dirección
            delta_effective = sum(self.d_buffer) / len(self.d_buffer)

            # distancia desde el punto inicial (única fuente de aceleración)
            dist_from_anchor = abs(pinch_dist_raw - self.anchor_pinch_dist)

            # 👉 ganancia SOLO por distancia del anchor
            gain = BASE_GAIN + dist_from_anchor * ACCEL_FACTOR

            zoom_steps = int(delta_effective * gain)

            # clamp
            if abs(zoom_steps) >= MIN_ZOOM_STEP:
                zoom_steps = max(
                    -MAX_ZOOM_STEP,
                    min(MAX_ZOOM_STEP, zoom_steps)
                )

                # pinch abriendo (delta positivo) = zoom in
                # pinch cerrando (delta negativo) = zoom out
                if delta_effective > 0:
                    # zoom in
                    for _ in range(abs(zoom_steps)):
                        pyautogui.hotkey('ctrl', '+')
                    events.append("ZOOM_IN")
                else:
                    # zoom out
                    for _ in range(abs(zoom_steps)):
                        pyautogui.hotkey('ctrl', '-')
                    events.append("ZOOM_OUT")

        self.prev_pinch_dist_raw = pinch_dist_raw
        return events

    # =====================
    # VALIDACIÓN
    # =====================
    def _validate_detection(self, center, hand_size, pinch_dist):
        """
        Valida que la detección sea consistente con el frame anterior.
        Solo se usa PRE-ARMADO.
        """
        if self.last_valid_center is None:
            return True

        # validar salto de posición
        position_jump = abs(center[1] - self.last_valid_center[1])
        if position_jump > MAX_POSITION_JUMP:
            print(f"[ZOOM] ⚠️ Salto de posición: {position_jump:.3f}")
            return False

        # validar cambio de tamaño de mano
        if hand_size is not None and self.last_valid_size is not None:
            size_change_ratio = abs(hand_size - self.last_valid_size) / self.last_valid_size
            if size_change_ratio > MAX_SIZE_CHANGE:
                print(f"[ZOOM] ⚠️ Cambio de tamaño: {size_change_ratio:.2%}")
                return False
        
        # validar salto de distancia pinch
        if pinch_dist is not None and self.last_valid_pinch is not None:
            pinch_jump = abs(pinch_dist - self.last_valid_pinch)
            if pinch_jump > MAX_PINCH_JUMP:
                print(f"[ZOOM] ⚠️ Salto de pinch: {pinch_jump:.3f}")
                return False

        return True

    # =====================
    # HELPERS
    # =====================
    def _euclidean_dist(self, p1, p2):
        """Distancia euclidiana entre dos puntos 2D"""
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) ** 0.5

    def _calculate_hand_size(self, hand_landmarks_raw):
        """Calcula el tamaño de la mano (distancia muñeca -> punta dedo medio)"""
        wrist = hand_landmarks_raw.landmark[0]
        middle_tip = hand_landmarks_raw.landmark[12]
        
        dx = middle_tip.x - wrist.x
        dy = middle_tip.y - wrist.y
        dz = middle_tip.z - wrist.z
        
        return (dx**2 + dy**2 + dz**2) ** 0.5
    
    def depth_intent_ok(self, hand_landmarks_raw):
        """Z solo para INTENCIÓN, no para amplificar ganancia"""
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
        self.prev_pinch_dist_raw = None
        self.zoom_active = False
        self.zoom_start_time = None
        self.anchor_pinch_dist = None
        self.hand_size = None
        self.smoothed_hand_size = None
        self.outlier_count = 0
        self.last_valid_center = None
        self.last_valid_size = None
        self.last_valid_pinch = None
        self.smoothed_center = None
        self.smoothed_pinch_dist = None
        self.d_buffer = []
        self.last_motion_time = None
        self.pinch_100ms_ago = None
        self.time_100ms_ago = None
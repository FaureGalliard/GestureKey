import time
import pyautogui
from utils.constants import (
    VOLUME_ARM_TIME,
    INTENT_Z_ENTER,
    INTENT_Z_EXIT
)
from utils.utils import hand_center


# =====================
# TUNING (IMPORTANTE)
# =====================
BASE_GAIN = 100            # ganancia mínima (menor que scroll, volumen es más sensible)
ACCEL_FACTOR = 200         # cuánto acelera al alejarte del punto inicial
MAX_VOLUME_STEP = 30       # límite de seguridad (steps de volumen)
MIN_VOLUME_STEP = 1        # mínimo cambio perceptible

# 🎯 NORMALIZACIÓN POR TAMAÑO DE MANO
REFERENCE_HAND_SIZE = 0.15  # tamaño típico de mano cercana (distancia muñeca-dedo medio)
SIZE_COMPENSATION = True    # activar normalización por tamaño
SIZE_RATIO_MIN = 0.7        # clamp inferior para evitar amplificaciones extremas
SIZE_RATIO_MAX = 1.4        # clamp superior

# 🛡️ PROTECCIÓN CONTRA ERRORES DE DETECCIÓN (solo pre-armado)
MAX_POSITION_JUMP = 0.15    # salto máximo permitido entre frames (15% de pantalla)
MAX_SIZE_CHANGE = 0.3       # cambio máximo de tamaño de mano (30%)
OUTLIER_RECOVERY_FRAMES = 2 # frames para recuperarse de un outlier

# 🎯 SUAVIZADO (solo para validación, no para dy)
POSITION_ALPHA = 0.7        # suavizado exponencial de posición
SIZE_ALPHA = 0.6            # suavizado del tamaño de mano

# 🥇 DEADZONE DE VELOCIDAD (mata micro-movimientos)
VELOCITY_DEADZONE = 0.0025  # umbral de velocidad mínima (ligeramente mayor que scroll)

# 🥈 INTEGRADOR TEMPORAL (suaviza dirección)
TEMPORAL_INTEGRATION_FRAMES = 3  # frames a acumular antes de cambiar volumen
DY_BUFFER_SIZE = 3               # tamaño del buffer

# 🥉 DETECCIÓN DE QUIETUD (mano quieta = no cambio)
MOTION_THRESHOLD = 0.0035   # movimiento mínimo para considerar "en movimiento"
STILLNESS_TIMEOUT = 0.1     # 100ms sin movimiento = quieto


class VolumeGesture:
    """Control de volumen robusto con protección contra errores de detección"""

    def __init__(self):
        self.prev_center_raw = None     # posición cruda para calcular dy
        self.volume_start_time = None
        self.volume_active = False
        self.intent_active = False

        # referencia para aceleración
        self.anchor_y = None
        
        # 🎯 tamaño de mano para normalización (suavizado)
        self.hand_size = None
        self.smoothed_hand_size = None
        
        # 🛡️ protección contra outliers (solo pre-armado)
        self.outlier_count = 0
        self.last_valid_center = None
        self.last_valid_size = None
        
        # 🎯 suavizado de posición (solo para validación)
        self.smoothed_center = None
        
        # 🥈 integrador temporal - buffer de dy
        self.dy_buffer = []
        
        # 🥉 detección de quietud
        self.last_motion_time = None
        self.position_100ms_ago = None
        self.time_100ms_ago = None

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

        center_raw = hand_center(main_hand)

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

        # ---- debug
        if hand_landmarks_raw is not None:
            depth = self._relative_depth(hand_landmarks_raw)
            print(
                f"[VOL] Y={center_raw[1]:.3f} "
                f"DEPTH={depth:.4f} "
                f"DIST_Z={distance_z:.4f} "
                f"SIZE={current_hand_size:.4f} "
                f"SIZE_SMOOTH={self.smoothed_hand_size:.4f} "
                f"OUTLIERS={self.outlier_count} "
                f"INTENT={self.intent_active} "
                f"ARMED={self.volume_active}"
            )

        # 🛡️ VALIDACIÓN DE OUTLIERS - SOLO PRE-ARMADO
        if not self.volume_active:
            is_valid_detection = self._validate_detection(self.smoothed_center, self.smoothed_hand_size)
            
            if not is_valid_detection:
                self.outlier_count += 1
                # si hay muchos outliers consecutivos, resetear
                if self.outlier_count > OUTLIER_RECOVERY_FRAMES:
                    print("[VOLUME] ⚠️ Demasiados outliers pre-armado - reseteando")
                    self._reset()
                # ignorar este frame pero no resetear inmediatamente
                return events
            else:
                # detección válida - resetear contador
                self.outlier_count = 0
                self.last_valid_center = self.smoothed_center
                self.last_valid_size = self.smoothed_hand_size

        # ---- intención por profundidad
        if hand_landmarks_raw is not None:
            if not self.depth_intent_ok(hand_landmarks_raw):
                self._reset()
                return events

        # ---- armado por tiempo
        if not self.volume_active:
            if self.volume_start_time is None:
                self.volume_start_time = now
                self.prev_center_raw = center_raw
                self.anchor_y = center_raw[1]   # 🎯 punto inicial
                self.hand_size = self.smoothed_hand_size  # 🎯 tamaño de referencia (suavizado)
                return events

            if now - self.volume_start_time < VOLUME_ARM_TIME:
                self.prev_center_raw = center_raw
                return events

            self.volume_active = True
            print("[VOLUME] ✅ Armado y activo")

        # =====================
        # VOLUMEN CON DY CRUDO (sin suavizado)
        # =====================
        if self.prev_center_raw is not None:
            # 👉 usar posición CRUDA para dy, no suavizada
            dy_raw = center_raw[1] - self.prev_center_raw[1]
            
            # 🎯 normalizar dy por cambio de tamaño de mano (con clamp para evitar amplificaciones extremas)
            if SIZE_COMPENSATION and self.smoothed_hand_size is not None and self.hand_size is not None and self.hand_size > 0:
                # si la mano es más pequeña (lejos), el mismo dy físico debe generar más cambio
                size_ratio = self.hand_size / self.smoothed_hand_size
                # 👉 CLAMP para evitar amplificaciones extremas por ruido
                size_ratio = max(SIZE_RATIO_MIN, min(SIZE_RATIO_MAX, size_ratio))
                dy_normalized = dy_raw * size_ratio
            else:
                dy_normalized = dy_raw

            # 🥇 DEADZONE DE VELOCIDAD - mata micro-movimientos
            if abs(dy_normalized) < VELOCITY_DEADZONE:
                dy_normalized = 0.0
            
            # 🥉 DETECCIÓN DE QUIETUD - actualizar estado de movimiento
            if abs(dy_normalized) > MOTION_THRESHOLD:
                self.last_motion_time = now
            else:
                # sin movimiento suficiente
                if self.last_motion_time and now - self.last_motion_time > STILLNESS_TIMEOUT:
                    # mano quieta por >100ms → no cambio de volumen
                    self.prev_center_raw = center_raw
                    return events
            
            # 🥉 DETECCIÓN DE QUIETUD - verificar desplazamiento total en 100ms
            if self.position_100ms_ago is None or self.time_100ms_ago is None:
                self.position_100ms_ago = center_raw[1]
                self.time_100ms_ago = now
            elif now - self.time_100ms_ago >= 0.1:
                # verificar movimiento total en últimos 100ms
                total_displacement = abs(center_raw[1] - self.position_100ms_ago)
                if total_displacement < MOTION_THRESHOLD:
                    # mano prácticamente quieta → no cambio de volumen
                    self.prev_center_raw = center_raw
                    return events
                # actualizar referencia de 100ms
                self.position_100ms_ago = center_raw[1]
                self.time_100ms_ago = now
            
            # 🥈 INTEGRADOR TEMPORAL - acumular dy en buffer
            if dy_normalized != 0.0:
                self.dy_buffer.append(dy_normalized)
                if len(self.dy_buffer) > DY_BUFFER_SIZE:
                    self.dy_buffer.pop(0)
            
            # esperar a tener suficientes muestras
            if len(self.dy_buffer) < TEMPORAL_INTEGRATION_FRAMES:
                self.prev_center_raw = center_raw
                return events
            
            # 👉 usar promedio del buffer para suavizar dirección
            dy_effective = sum(self.dy_buffer) / len(self.dy_buffer)

            # distancia desde el punto inicial (única fuente de aceleración)
            dist_from_anchor = abs(center_raw[1] - self.anchor_y)

            # 👉 ganancia SOLO por distancia del anchor (sin Z factor)
            # Z se usa solo para intención, no para amplificar
            gain = BASE_GAIN + dist_from_anchor * ACCEL_FACTOR

            volume_steps = int(dy_effective * gain)

            # clamp
            if abs(volume_steps) >= MIN_VOLUME_STEP:
                volume_steps = max(
                    -MAX_VOLUME_STEP,
                    min(MAX_VOLUME_STEP, volume_steps)
                )

                # mano arriba (dy negativo) = subir volumen
                # mano abajo (dy positivo) = bajar volumen
                if dy_effective < 0:
                    # subir volumen
                    for _ in range(abs(volume_steps)):
                        pyautogui.press('volumeup')
                    events.append("VOLUME_UP")
                else:
                    # bajar volumen
                    for _ in range(abs(volume_steps)):
                        pyautogui.press('volumedown')
                    events.append("VOLUME_DOWN")

        self.prev_center_raw = center_raw
        return events

    # =====================
    # VALIDACIÓN
    # =====================
    def _validate_detection(self, center, hand_size):
        """
        Valida que la detección sea consistente con el frame anterior.
        Retorna False si detecta un outlier (error de tracking).
        Solo se usa PRE-ARMADO.
        """
        # primera detección siempre es válida
        if self.last_valid_center is None:
            return True

        # validar salto de posición
        position_jump = abs(center[1] - self.last_valid_center[1])
        if position_jump > MAX_POSITION_JUMP:
            print(f"[VOLUME] ⚠️ Salto de posición: {position_jump:.3f}")
            return False

        # validar cambio de tamaño de mano
        if hand_size is not None and self.last_valid_size is not None:
            size_change_ratio = abs(hand_size - self.last_valid_size) / self.last_valid_size
            if size_change_ratio > MAX_SIZE_CHANGE:
                print(f"[VOLUME] ⚠️ Cambio de tamaño: {size_change_ratio:.2%}")
                return False

        return True

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
        self.prev_center_raw = None
        self.volume_active = False
        self.volume_start_time = None
        self.anchor_y = None
        self.hand_size = None
        self.smoothed_hand_size = None
        self.outlier_count = 0
        self.last_valid_center = None
        self.last_valid_size = None
        self.smoothed_center = None
        self.dy_buffer = []
        self.last_motion_time = None
        self.position_100ms_ago = None
        self.time_100ms_ago = None
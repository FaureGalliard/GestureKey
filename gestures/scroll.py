"""
ScrollGesture — two-finger vertical scroll.

Fixes vs. previous version:
  - Depth gate removed entirely (no more Z-intent requirement).
  - Buffer is CLEARED on stillness instead of just returning — this was
    the root cause of scroll firing after stopping: stale dy values from
    a previous movement remained in the buffer and kept triggering scroll
    once the hand went still.
  - 100 ms displacement check also clears the buffer when quiet.
  - VELOCITY_DEADZONE applied before the stillness timer so micro-noise
    doesn't reset the stillness clock.
"""
from __future__ import annotations
from typing import List

import pyautogui

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from utils.geometry import hand_center

pyautogui.PAUSE = 0.01

# ---- tuning -----------------------------------------------------------
BASE_GAIN               = 10_000
ACCEL_FACTOR            = 12_000
MAX_SCROLL_STEP         = 80_000
MIN_SCROLL_STEP         = 10

SIZE_COMPENSATION       = True
SIZE_RATIO_MIN          = 0.7
SIZE_RATIO_MAX          = 1.4
SIZE_ALPHA              = 0.6

POSITION_ALPHA          = 0.7
MAX_POSITION_JUMP       = 0.15
MAX_SIZE_CHANGE         = 0.30
OUTLIER_RECOVERY_FRAMES = 2

# Velocidad mínima para considerar que hay movimiento real.
# Por debajo de esto → dy se trata como 0 y se limpia el buffer.
VELOCITY_DEADZONE       = 0.003

# Frames del buffer temporal — todos deben superar la deadzone
# para que el promedio no arrastre valores viejos.
TEMPORAL_FRAMES         = 3

# Tiempo sin movimiento real antes de declarar "quieto" y limpiar buffer.
STILLNESS_TIMEOUT       = 0.12


class ScrollGesture(Gesture):
    NAME = "SCROLL"

    def __init__(self, arm_time: float = 0.18) -> None:
        self._arm_time = arm_time
        self.reset()

    # ------------------------------------------------------------------
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []

        if frame_data.state != HandState.TWO_FINGERS:
            self.reset()
            return events

        main_hand = frame_data.main_hand
        hand_raw  = frame_data.main_hand_raw
        now       = frame_data.timestamp

        if main_hand is None:
            return events

        center_raw        = hand_center(main_hand)
        current_hand_size = self._calc_hand_size(hand_raw) if hand_raw else None

        # ---- suavizado de tamaño de mano (normalización) --------------
        if self._smoothed_hand_size is None:
            self._smoothed_hand_size = current_hand_size
        elif current_hand_size is not None:
            self._smoothed_hand_size = (
                SIZE_ALPHA * current_hand_size
                + (1 - SIZE_ALPHA) * self._smoothed_hand_size
            )

        # ---- suavizado de posición (solo para validación pre-armado) --
        if self._smoothed_center is None:
            self._smoothed_center = center_raw
        else:
            self._smoothed_center = (
                POSITION_ALPHA * center_raw[0] + (1 - POSITION_ALPHA) * self._smoothed_center[0],
                POSITION_ALPHA * center_raw[1] + (1 - POSITION_ALPHA) * self._smoothed_center[1],
            )

        # ---- rechazo de outliers (solo pre-armado) --------------------
        if not self._active:
            if not self._valid_detection(self._smoothed_center, self._smoothed_hand_size):
                self._outlier_count += 1
                if self._outlier_count > OUTLIER_RECOVERY_FRAMES:
                    self.reset()
                return events
            self._outlier_count     = 0
            self._last_valid_center = self._smoothed_center
            self._last_valid_size   = self._smoothed_hand_size

        # ---- armado por tiempo ----------------------------------------
        if not self._active:
            if self._start_time is None:
                self._start_time      = now
                self._prev_center_raw = center_raw
                self._anchor_y        = center_raw[1]
                self._ref_hand_size   = self._smoothed_hand_size
                return events
            if now - self._start_time < self._arm_time:
                self._prev_center_raw = center_raw
                return events
            self._active = True

        # ---- cálculo de scroll ----------------------------------------
        if self._prev_center_raw is not None:
            dy_raw = center_raw[1] - self._prev_center_raw[1]

            # Normalización por tamaño de mano
            if (SIZE_COMPENSATION
                    and self._smoothed_hand_size
                    and self._ref_hand_size
                    and self._ref_hand_size > 0):
                ratio = max(SIZE_RATIO_MIN, min(SIZE_RATIO_MAX,
                            self._ref_hand_size / self._smoothed_hand_size))
                dy = dy_raw * ratio
            else:
                dy = dy_raw

            # Deadzone — movimiento por debajo de esto = 0
            if abs(dy) < VELOCITY_DEADZONE:
                dy = 0.0

            # ── QUIETUD ──────────────────────────────────────────────
            # Si dy es 0 (debajo de deadzone), actualizamos el reloj de
            # quietud. Cuando la mano lleva más de STILLNESS_TIMEOUT
            # segundos sin moverse, LIMPIAMOS el buffer para que los
            # valores viejos de la última pasada no sigan disparando scroll.
            if dy == 0.0:
                if self._last_motion_time is None:
                    # primera vez quieto tras armado — iniciar reloj
                    self._last_motion_time = now
                elif now - self._last_motion_time > STILLNESS_TIMEOUT:
                    # quieto demasiado tiempo → limpiar buffer y salir
                    self._dy_buffer.clear()
                    self._prev_center_raw = center_raw
                    return events
                # quieto pero todavía dentro del timeout → salir sin scroll
                self._prev_center_raw = center_raw
                return events
            else:
                # hay movimiento real → resetear reloj de quietud
                self._last_motion_time = None

            # ── BUFFER TEMPORAL ───────────────────────────────────────
            # Solo se añaden valores que superaron la deadzone (dy != 0).
            # Así el promedio siempre refleja movimiento intencional.
            self._dy_buffer.append(dy)
            if len(self._dy_buffer) > TEMPORAL_FRAMES:
                self._dy_buffer.pop(0)

            if len(self._dy_buffer) < TEMPORAL_FRAMES:
                self._prev_center_raw = center_raw
                return events

            dy_eff      = sum(self._dy_buffer) / len(self._dy_buffer)
            dist_anchor = abs(center_raw[1] - self._anchor_y)
            gain        = BASE_GAIN + dist_anchor * ACCEL_FACTOR
            amount      = int(dy_eff * gain)

            if abs(amount) >= MIN_SCROLL_STEP:
                amount = max(-MAX_SCROLL_STEP, min(MAX_SCROLL_STEP, amount))
                pyautogui.scroll(-amount)
                events.append(GestureEvent.SCROLL)

        self._prev_center_raw = center_raw
        return events

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._prev_center_raw:    object = None
        self._active:             bool   = False
        self._start_time:         object = None
        self._anchor_y:           object = None
        self._ref_hand_size:      object = None
        self._smoothed_hand_size: object = None
        self._outlier_count:      int    = 0
        self._last_valid_center:  object = None
        self._last_valid_size:    object = None
        self._smoothed_center:    object = None
        self._dy_buffer:          list   = []
        self._last_motion_time:   object = None  # reloj de quietud

    # ------------------------------------------------------------------
    def _valid_detection(self, center, hand_size) -> bool:
        if self._last_valid_center is None:
            return True
        if abs(center[1] - self._last_valid_center[1]) > MAX_POSITION_JUMP:
            return False
        if (hand_size and self._last_valid_size and self._last_valid_size > 0
                and abs(hand_size - self._last_valid_size) / self._last_valid_size > MAX_SIZE_CHANGE):
            return False
        return True

    @staticmethod
    def _calc_hand_size(hand_raw) -> float:
        w, m = hand_raw.landmark[0], hand_raw.landmark[12]
        return ((m.x - w.x) ** 2 + (m.y - w.y) ** 2 + (m.z - w.z) ** 2) ** 0.5
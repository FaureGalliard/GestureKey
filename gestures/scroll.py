import time
import pyautogui
from utils.constants import (
    SCROLL_DEADZONE,
    SCROLL_TRIGGER,
    SCROLL_COOLDOWN,
    SCROLL_ARM_TIME,
    SCROLL_MAX_TIME,
    INTENT_Z_ENTER,
    INTENT_Z_EXIT
)
from utils.utils import hand_center


class ScrollGesture:
    """Gesto de scroll con dos dedos - modo trackpad (bidireccional)"""

    def __init__(self):
        # Movimiento
        self.scroll_accum = 0.0
        self.scroll_last_time = 0.0
        self.prev_center = None

        # Armado por tiempo
        self.scroll_start_time = None
        self.scroll_active = False

        # Intención por profundidad
        self.intent_active = False

        pyautogui.PAUSE = 0.01

    # =====================
    # MAIN DETECTOR
    # =====================
    def detect(self, state, main_hand, hand_landmarks_raw=None):
        events = []
        now = time.time()

        # -------- FILTRO 1: estado correcto
        if state != "TWO_FINGERS":
            self._reset()
            return events

        center = hand_center(main_hand)

        # -------- DEBUG
        if hand_landmarks_raw is not None:
            depth = self._relative_depth(hand_landmarks_raw)
            print(
                f"Y={center[1]:.2f} "
                f"DEPTH={depth:.4f} "
                f"INTENT={self.intent_active} "
                f"ARMED={self.scroll_active}"
            )

        # -------- FILTRO 2: intención por profundidad
        if hand_landmarks_raw is not None:
            if not self.depth_intent_ok(hand_landmarks_raw):
                self._reset()
                return events

        # -------- FILTRO 3: armado por tiempo
        if not self.scroll_active:
            if self.scroll_start_time is None:
                self.scroll_start_time = now
                self.prev_center = center
                return events

            if now - self.scroll_start_time < SCROLL_ARM_TIME:
                self.prev_center = center
                return events

            self.scroll_active = True  # 🔥 ARMADO

        # -------- FILTRO 4: timeout máximo
        if now - self.scroll_start_time > SCROLL_MAX_TIME:
            self._reset()
            return events

        # -------- MOVIMIENTO (TRACKPAD)
        if self.prev_center is not None:
            dy = center[1] - self.prev_center[1]

            # zona muerta
            if abs(dy) > SCROLL_DEADZONE:
                self.scroll_accum += dy

            # -------- TRIGGER CONTINUO
            if abs(self.scroll_accum) > SCROLL_TRIGGER:
                if now - self.scroll_last_time > SCROLL_COOLDOWN:
                    direction = "UP" if self.scroll_accum < 0 else "DOWN"
                    self._execute_scroll(direction)
                    events.append(f"SCROLL_{direction}")
                    self.scroll_last_time = now

                    # ⚠️ importante: no resetear a 0, solo amortiguar
                    self.scroll_accum *= 0.3

        self.prev_center = center
        return events

    # =====================
    # HELPERS
    # =====================
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

    def _execute_scroll(self, direction):
        try:
            pyautogui.scroll(120 if direction == "UP" else -120)
        except Exception as e:
            print(f"Scroll error: {e}")

    def _reset(self):
        self.prev_center = None
        self.scroll_accum = 0.0
        self.scroll_active = False
        self.scroll_start_time = None
        # intent_active NO se resetea (histeresis)

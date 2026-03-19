from __future__ import annotations
import time
from typing import Optional

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from app.config import AppConfig
from core.camera import Camera
from core.hand_tracker import HandTracker
from core.state_classifier import StateClassifier
from core.state_stabilizer import StateStabilizer
from core.gesture_manager import GestureManager
from core.cooldown_manager import CooldownManager
from domain.enums import HandState, GestureEvent
from domain.models import FrameData


class CameraWorker(QThread):
    frame_ready   = pyqtSignal(np.ndarray)
    state_changed = pyqtSignal(object, object, float)
    event_fired   = pyqtSignal(object)
    status_msg    = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config  = config
        self._running = False
        self._camera:     Optional[Camera]          = None
        self._tracker:    Optional[HandTracker]     = None
        self._classifier: Optional[StateClassifier] = None
        self._stabilizer: Optional[StateStabilizer] = None
        self._manager:    Optional[GestureManager]  = None

    def run(self) -> None:
        cfg = self._config

        try:
            self._camera     = Camera(cfg.camera_device, cfg.fps_limit)
            self._tracker    = HandTracker()
            self._classifier = StateClassifier(cfg.model_path)
            self._stabilizer = StateStabilizer(
                window=cfg.state_window,
                consensus=cfg.state_consensus,
                min_confidence=cfg.min_confidence,
            )
            cooldown      = CooldownManager(default_cooldown=cfg.cooldown)
            self._manager = GestureManager(cooldown)
        except Exception as exc:
            self.status_msg.emit(f"[ERROR] Inicialización: {exc}")
            return

        self._running = True
        prev_stable: HandState | None = None
        self.status_msg.emit("Pipeline iniciado")

        while self._running:
            frame = self._camera.read()
            if frame is None:
                self.status_msg.emit("[WARN] Frame vacío — reintentando")
                time.sleep(0.05)
                continue

            hands_data, hands_raw = self._tracker.process(frame)

            if hands_data:
                raw_state, confidence = self._classifier.predict(hands_data)
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0

            self._stabilizer.update(raw_state, confidence)
            current = self._stabilizer.current or HandState.NO_HANDS

            if current != prev_stable:
                self.status_msg.emit(f"[STATE] {prev_stable} → {current}")
                prev_stable = current

            self.state_changed.emit(current, raw_state, confidence)

            if current not in (HandState.NO_HANDS, HandState.UNKNOWN):
                frame_data = FrameData(
                    state=current,
                    hands=hands_data,
                    hands_raw=hands_raw,
                    timestamp=time.time(),
                )
                events = self._manager.process(frame_data)
                for event in events:
                    self.status_msg.emit(f"[EVENT] {event.value}")
                    self.event_fired.emit(event)

            self.frame_ready.emit(frame.copy())

        self._cleanup()

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def _cleanup(self) -> None:
        if self._camera:
            self._camera.release()
        if self._tracker:
            self._tracker.release()
        self.status_msg.emit("Pipeline detenido")
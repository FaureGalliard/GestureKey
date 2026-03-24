from __future__ import annotations
import time
from typing import Optional

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from config import AppConfig
from pipeline.camera import Camera
from pipeline.tracker import HandTracker
from pipeline.classifier import StateClassifier
from pipeline.stabilizer import StateStabilizer
from pipeline.gesture_manager import GestureManager
from pipeline.cooldown import CooldownManager
from utils.enums import HandState, GestureEvent
from utils.models import FrameData
import traceback
_NO_PENDING = -1


class CameraWorker(QThread):
    frame_ready     = pyqtSignal(np.ndarray)
    state_changed   = pyqtSignal(object, object, float)
    event_fired     = pyqtSignal(object)
    status_msg      = pyqtSignal(str)
    hands_changed   = pyqtSignal(list)
    camera_switched = pyqtSignal(int) 

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config  = config
        self._running = False

        self._camera:     Optional[Camera]          = None
        self._tracker:    Optional[HandTracker]     = None
        self._classifier: Optional[StateClassifier] = None
        self._stabilizer: Optional[StateStabilizer] = None
        self._manager:    Optional[GestureManager]  = None

        self._pending_device: int = _NO_PENDING
        self._active_device:  int = config.camera_device

    # ── public API (GUI thread) ───────────────────────────────────────────────

    def switch_camera(self, device: int) -> None:
        if device == self._active_device:
            return
        self._pending_device = device

    def stop(self) -> None:
        self._running = False

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        cfg = self._config
        try:
            # Estas clases ahora lanzan errores descriptivos gracias a los cambios anteriores
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
        except RuntimeError as e:
            self.status_msg.emit(f"[ERROR CRÍTICO] {e}")
            return
        except Exception as exc:
            traceback.print_exc() 
            self.status_msg.emit(f"[ERROR INESPERADO] {exc}")
            return

        self._running       = True
        self._active_device = cfg.camera_device
        prev_stable: HandState | None = None
        prev_hands:  list             = []
        self.status_msg.emit("Pipeline started")

        while self._running:

            # ── pending switch? ───────────────────────────────────────────────
            pending = self._pending_device
            if pending != _NO_PENDING:
                self._pending_device = _NO_PENDING
                self._do_switch(pending)
                prev_stable = None
                prev_hands  = []
                self._stabilizer.reset()
                self._manager.reset_all()

            # ── capture ───────────────────────────────────────────────────────
            if self._camera is None:
                time.sleep(0.05)
                continue

            frame = self._camera.read()
            if frame is None:
                self.status_msg.emit("[WARN] Empty frame — retrying")
                time.sleep(0.05)
                continue

            # ── tracking ──────────────────────────────────────────────────────
            hands_data, hands_raw = self._tracker.process(frame)

            # ── classification ────────────────────────────────────────────────
            if hands_data:
                raw_state, confidence = self._classifier.predict(hands_data)
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0

            # ── stabilisation ─────────────────────────────────────────────────
            self._stabilizer.update(raw_state, confidence)
            current = self._stabilizer.current or HandState.NO_HANDS

            if current != prev_stable:
                self.status_msg.emit(f"[STATE] {prev_stable} → {current}")
                prev_stable = current

            self.state_changed.emit(current, raw_state, confidence)

            # ── hands changed ─────────────────────────────────────────────────
            detected_hands = list(hands_data.keys())
            if detected_hands != prev_hands:
                self.hands_changed.emit(detected_hands)
                prev_hands = detected_hands

            # ── gesture detection ─────────────────────────────────────────────
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

            # ── broadcast frame ───────────────────────────────────────────────
            self.frame_ready.emit(frame.copy())

        self._cleanup()

    # ── private helpers ───────────────────────────────────────────────────────

    def _do_switch(self, device: int) -> None:
        fallback = self._active_device

        if self._camera is not None:
            self._camera.release()
            self._camera = None

        self.status_msg.emit(f"[CAM] Switching → device {device}")
        try:
            self._camera        = Camera(device, self._config.fps_limit)
            self._active_device = device
            self.status_msg.emit(f"[CAM] Opened device {device}")
            self.camera_switched.emit(device)
        except Exception as exc:
            self.status_msg.emit(f"[CAM] Failed to open device {device}: {exc}")
            if device != fallback:
                try:
                    self._camera        = Camera(fallback, self._config.fps_limit)
                    self._active_device = fallback
                    self.status_msg.emit(f"[CAM] Fell back to device {fallback}")
                    self.camera_switched.emit(fallback)
                except Exception as exc2:
                    self.status_msg.emit(f"[CAM] Fallback also failed: {exc2}")
                    self.camera_switched.emit(-1)
            else:
                self.camera_switched.emit(-1)

    def _cleanup(self) -> None:
        if self._camera:
            self._camera.release()
        if self._tracker:
            self._tracker.release()
        self.status_msg.emit("Pipeline stopped")
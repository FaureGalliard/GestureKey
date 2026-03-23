from __future__ import annotations
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSizePolicy,
)

from domain.enums import HandState, GestureEvent
from ui.components.camera_view import CameraView
from ui.components.console import Console
from ui.components.toolbar import Toolbar
from ui.components.theme import BG_MAIN, BG_CAMERA, BASE_STYLE

_PANEL_WIDTH = 240


class MainWindow(QMainWindow):
    request_settings = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("GestureKey")
        self.setStyleSheet(BASE_STYLE + f"QMainWindow {{ background: {BG_MAIN}; }}")
        self._console_visible = False
        self._size_set = False
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background:{BG_MAIN};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Console panel
        self._console = Console()
        self._console.setFixedWidth(0)
        self._console.hide()
        root.addWidget(self._console)

        # Camera view — fills remaining space
        self._camera_view = CameraView()
        self._camera_view.setStyleSheet(f"background:{BG_CAMERA};")
        self._camera_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self._camera_view, stretch=1)

        # Toolbar — parented to the QMainWindow itself, not central widget.
        # This places it above all central-widget repaints in the z-stack,
        # so camera frame updates can never push it behind the camera feed.
        self._toolbar = Toolbar(self)
        self._toolbar.toggle_console.connect(self._toggle_console)
        self._toolbar.toggle_active.connect(self._on_toggle_active)
        self._toolbar.open_settings.connect(self.request_settings.emit)
        self._toolbar.geometry_changed.connect(self._reposition_toolbar)
        self._toolbar.show()
        self._toolbar.raise_()

    # ── toolbar positioning ───────────────────────────────────────────────────

    def _reposition_toolbar(self) -> None:
        self._toolbar.adjustSize()
        # Position relative to the QMainWindow frame.
        # We want top-right of the *camera area* (central widget right edge).
        # central widget starts at x = 0 within QMainWindow's content area,
        # but QMainWindow adds a 1px frame — use geometry() for accuracy.
        cw = self.centralWidget()
        if cw is None:
            return
        # Map top-right of central widget into QMainWindow coordinates
        top_right = cw.mapTo(self, cw.rect().topRight())
        x = top_right.x() - self._toolbar.width() - 16
        y = cw.mapTo(self, cw.rect().topLeft()).y() + 16
        self._toolbar.move(x, y)
        self._toolbar.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_toolbar()

    # ── console slide ─────────────────────────────────────────────────────────

    def _toggle_console(self) -> None:
        self._console_visible = not self._console_visible

        if self._console_visible:
            self._console.setFixedWidth(0)
            self._console.show()

        anim = QPropertyAnimation(self._console, b"maximumWidth", self)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        if self._console_visible:
            anim.setStartValue(0)
            anim.setEndValue(_PANEL_WIDTH)
        else:
            anim.setStartValue(_PANEL_WIDTH)
            anim.setEndValue(0)
            anim.finished.connect(self._console.hide)

        anim.valueChanged.connect(lambda _: self._reposition_toolbar())
        anim.start()
        self._toolbar.set_console_state(self._console_visible)

    def _on_toggle_active(self) -> None:
        pass

    # ── worker slots ──────────────────────────────────────────────────────────

    def on_frame(self, frame: np.ndarray) -> None:
        if not self._size_set:
            h, w = frame.shape[:2]
            self.resize(w, h)
            self._size_set = True
        self._camera_view.update_frame(frame)

    def on_state_changed(self, stable: HandState, raw: HandState, confidence: float) -> None:
        self._console.on_state_changed(stable, raw, confidence)

    def on_hands_changed(self, hands: list[str]) -> None:
        self._console.on_hands_changed(hands)

    def on_event(self, event: GestureEvent) -> None:
        self._console.on_event(event)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
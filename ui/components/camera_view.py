from __future__ import annotations
import numpy as np
import cv2
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy
from ui.theme import BG_CAMERA


class CameraView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background:{BG_CAMERA};")
        self._raw_pixmap: QPixmap | None = None
        self._overlay_text: str = ""       # non-empty = show overlay
        self._dot_count: int = 0
        self._base_text: str = ""

        # Animated dots timer — ticks while overlay is shown
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(500)
        self._dot_timer.timeout.connect(self._tick_dots)

    # ── public API ────────────────────────────────────────────────────────────

    def update_frame(self, frame: np.ndarray) -> None:
        """Display a live camera frame and hide any overlay."""
        self._overlay_text = ""
        self._base_text    = ""
        self._dot_timer.stop()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.flip(frame_rgb, 1)
        h, w, ch  = frame_rgb.shape
        img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._raw_pixmap = QPixmap.fromImage(img)
        self.update()

    def show_overlay(self, message: str, animate: bool = False) -> None:
        """
        Cover the view with a dark overlay + pill message.
        If animate=True the dots after the message cycle (…).
        """
        self._base_text    = message
        self._dot_count    = 0
        self._overlay_text = message
        self._raw_pixmap   = None
        if animate:
            self._dot_timer.start()
        else:
            self._dot_timer.stop()
        self.update()

    # legacy alias used by main_window
    def clear(self, message: str = "Selecting camera…") -> None:
        self.show_overlay(message, animate=False)

    # ── internals ─────────────────────────────────────────────────────────────

    def _tick_dots(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        self._overlay_text = self._base_text + "." * self._dot_count
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(BG_CAMERA) if BG_CAMERA.startswith("#") else QColor("#0d0d0d")
        p.fillRect(self.rect(), bg)

        if self._overlay_text:
            # Semi-transparent dark wash over whatever was last painted
            p.fillRect(self.rect(), QColor(0, 0, 0, 210))

            text  = self._overlay_text
            font  = QFont("Consolas", 10, QFont.Weight.DemiBold)
            p.setFont(font)
            fm    = p.fontMetrics()
            tw    = fm.horizontalAdvance(text)
            th    = fm.height()
            pad_x, pad_y = 20, 10
            pill_w = tw + pad_x * 2
            pill_h = th + pad_y * 2
            pill_x = (self.width()  - pill_w) // 2
            pill_y = (self.height() - pill_h) // 2

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)
            p.setPen(QColor(255, 255, 255, 40))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)
            p.setPen(QColor(255, 255, 255, 160))
            p.drawText(pill_x + pad_x, pill_y + pad_y + fm.ascent(), text)

        elif self._raw_pixmap is not None:
            scaled = self._raw_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width()  - scaled.width())  // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)

        p.end()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()
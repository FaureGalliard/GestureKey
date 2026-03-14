from __future__ import annotations
from collections import deque

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QSizePolicy, QFrame,
)

from domain.enums import HandState, GestureEvent

_STATE_BRIGHTNESS: dict[HandState, int] = {
    HandState.PALM:          20,
    HandState.FIST:          60,
    HandState.PINCH:         100,
    HandState.TWO_FINGERS:   40,
    HandState.THREE_FINGERS: 80,
    HandState.FOUR_FINGERS:  50,
    HandState.UNKNOWN:       160,
    HandState.NO_HANDS:      200,
}
_DEFAULT_BRIGHTNESS = 120


class CameraWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stable_state: HandState = HandState.NO_HANDS
        self._raw_state:    HandState = HandState.NO_HANDS
        self._confidence:   float     = 0.0
        self._state_buffer: deque     = deque(maxlen=6)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gesture Control")
        self.setMinimumSize(900, 540)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #1a1a1a;
                font-family: 'Consolas', 'Menlo', monospace;
            }
            QLabel#section_title {
                font-size: 10px;
                font-weight: bold;
                color: #aaaaaa;
                letter-spacing: 2px;
                padding: 0;
            }
            QLabel#state_label {
                font-size: 20px;
                font-weight: bold;
                padding: 6px 10px;
                border-radius: 4px;
                background: #f5f5f5;
                color: #1a1a1a;
                border: 1px solid #1a1a1a;
            }
            QLabel#raw_label {
                font-size: 11px;
                color: #888888;
                padding: 1px 0;
            }
            QTextEdit#log {
                background-color: #f8f8f8;
                color: #555555;
                font-size: 10px;
                border: 1px solid #dddddd;
                border-radius: 4px;
            }
            QLabel { color: #1a1a1a; }
            QScrollBar:vertical {
                background: #f5f5f5;
                width: 4px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                border-radius: 2px;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._camera_label = QLabel()
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._camera_label.setStyleSheet("background:#f0f0f0;")
        root.addWidget(self._camera_label, stretch=1)

        panel = QWidget()
        panel.setFixedWidth(200)
        panel.setStyleSheet("background:#ffffff; border-left: 1px solid #e0e0e0;")
        right = QVBoxLayout(panel)
        right.setContentsMargins(12, 14, 12, 14)
        right.setSpacing(10)

        t1 = QLabel("STATE")
        t1.setObjectName("section_title")
        right.addWidget(t1)

        self._state_label = QLabel(HandState.NO_HANDS.value)
        self._state_label.setObjectName("state_label")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self._state_label)

        self._raw_label = QLabel("Raw: —  (0.0%)")
        self._raw_label.setObjectName("raw_label")
        right.addWidget(self._raw_label)

        self._conf_bar = _ConfidenceBar()
        right.addWidget(self._conf_bar)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background:#e0e0e0; border:none; max-height:1px;")
        right.addWidget(sep1)

        t2 = QLabel("BUFFER")
        t2.setObjectName("section_title")
        right.addWidget(t2)

        buf_grid = QHBoxLayout()
        buf_grid.setSpacing(3)
        self._buf_labels: list[QLabel] = []
        for _ in range(6):
            lbl = QLabel("·")
            lbl.setFixedWidth(26)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "background:#ffffff; border:1px solid #dddddd; border-radius:3px;"
                "padding:1px 0; font-size:9px; color:#bbbbbb;"
            )
            buf_grid.addWidget(lbl)
            self._buf_labels.append(lbl)
        right.addLayout(buf_grid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:#e0e0e0; border:none; max-height:1px;")
        right.addWidget(sep2)

        t3 = QLabel("CONSOLE")
        t3.setObjectName("section_title")
        right.addWidget(t3)

        self._log = QTextEdit()
        self._log.setObjectName("log")
        self._log.setReadOnly(True)
        right.addWidget(self._log, stretch=1)

        root.addWidget(panel)

    def on_frame(self, frame: np.ndarray) -> None:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.flip(frame_rgb, 1)

        h, w, ch = frame_rgb.shape
        img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._camera_label.setPixmap(pix)

    def on_state_changed(
        self, stable: HandState, raw: HandState, confidence: float
    ) -> None:
        self._stable_state = stable
        self._raw_state    = raw
        self._confidence   = confidence
        self._state_buffer.append(stable)

        v = _STATE_BRIGHTNESS.get(stable, _DEFAULT_BRIGHTNESS)
        self._state_label.setText(stable.value)
        self._state_label.setStyleSheet(
            f"font-size:20px; font-weight:bold; padding:6px 10px; border-radius:4px;"
            f"background:#f5f5f5; color:rgb({v},{v},{v}); border:1px solid #1a1a1a;"
        )

        raw_v = 100 if confidence >= 0.6 else 180
        self._raw_label.setStyleSheet(
            f"font-size:11px; padding:1px 0; color:rgb({raw_v},{raw_v},{raw_v});"
        )
        self._raw_label.setText(f"Raw: {raw.value}  ({confidence*100:.1f}%)")

        self._conf_bar.set_value(confidence)

        buf_list = list(self._state_buffer)
        for i, lbl in enumerate(self._buf_labels):
            if i < len(buf_list):
                s  = buf_list[i]
                sv = _STATE_BRIGHTNESS.get(s, _DEFAULT_BRIGHTNESS)
                lbl.setText(s.value[:3])
                lbl.setStyleSheet(
                    f"background:rgb({sv},{sv},{sv});"
                    f"color:{'#ffffff' if sv < 128 else '#1a1a1a'};"
                    f"border:1px solid #1a1a1a;"
                    f"border-radius:3px; padding:1px 0; font-size:9px;"
                )
            else:
                lbl.setText("·")
                lbl.setStyleSheet(
                    "background:#ffffff; border:1px solid #dddddd; border-radius:3px;"
                    "padding:1px 0; font-size:9px; color:#bbbbbb;"
                )

    def on_event(self, event: GestureEvent) -> None:
        self._log.append(f"<span style='color:#1a1a1a'>&#9658; {event.value}</span>")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_status(self, msg: str) -> None:
        if msg.startswith("[EVENT]") or msg.startswith("[STATE]"):
            self._log.append(f"<span style='color:#333333'>{msg}</span>")
        elif msg.startswith("[ERROR]"):
            self._log.append(f"<span style='color:#1a1a1a;font-weight:bold'>{msg}</span>")
        else:
            self._log.append(f"<span style='color:#aaaaaa'>{msg}</span>")

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()


class _ConfidenceBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self.setFixedHeight(10)

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setBrush(QBrush(QColor(235, 235, 235)))
        p.setPen(QPen(QColor(200, 200, 200), 1))
        p.drawRoundedRect(0, 0, w, h, 3, 3)

        fill_w = int(w * self._value)
        if fill_w > 2:
            v = 26 if self._value >= 0.75 else (80 if self._value >= 0.60 else 160)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(v, v, v)))
            p.drawRoundedRect(1, 1, fill_w - 2, h - 2, 2, 2)
        p.end()
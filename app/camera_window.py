"""
CameraWindow — ventana flotante que muestra el feed de la cámara con
overlays informativos idénticos a los que mostraba OpenCV, pero ahora
integrados en PyQt6.

Se abre/cierra al hacer click en el ícono del system tray.
"""
from __future__ import annotations
from collections import deque
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QSizePolicy, QFrame,
)

from domain.enums import HandState, GestureEvent

# ---- Colores por estado (RGB para Qt) ---------------------------------
_STATE_COLORS: dict[HandState, tuple[int, int, int]] = {
    HandState.PALM:          (80,  220,  80),
    HandState.FIST:          (220,  60,  60),
    HandState.PINCH:         (200,  60, 200),
    HandState.TWO_FINGERS:   (220, 200,  40),
    HandState.THREE_FINGERS: (40,  200, 220),
    HandState.FOUR_FINGERS:  (220, 140,  40),
    HandState.UNKNOWN:       (140, 140, 140),
    HandState.NO_HANDS:      (80,  80,  80),
}
_DEFAULT_COLOR = (200, 200, 200)


def _qcolor(state: HandState) -> QColor:
    r, g, b = _STATE_COLORS.get(state, _DEFAULT_COLOR)
    return QColor(r, g, b)


class CameraWindow(QWidget):
    """
    Ventana principal de visualización.

    Características:
    - Feed de cámara con landmarks ya dibujados por HandTracker.
    - Overlay HUD: estado estable, predicción raw, confianza, buffer.
    - Panel lateral con log de eventos en tiempo real.
    - Botón para cerrar/ocultar (no termina la app).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stable_state: HandState    = HandState.NO_HANDS
        self._raw_state:    HandState    = HandState.NO_HANDS
        self._confidence:   float        = 0.0
        self._state_buffer: deque        = deque(maxlen=6)
        self._last_events:  list[str]    = []

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWindowTitle("Gesture Control — Vista de cámara")
        self.setMinimumSize(860, 520)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #e0e0e0;
                font-family: 'Segoe UI', Consolas, monospace;
            }
            QLabel#title {
                font-size: 14px;
                font-weight: bold;
                color: #F5F5FC;
                padding: 4px 0;
            }
            QLabel#state_label {
                font-size: 22px;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
                background: #181924;
            }
            QLabel#raw_label {
                font-size: #574C4C;
                color: #888;
                padding: 2px 0;
            }
            QTextEdit#log {
                background-color: ###574C4C;
                color: #7ec8a0;
                font-size: 11px;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QPushButton {
                background-color: ##3F3737;
                color: #a0c4ff;
                border: 1px solid #334;
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: ##1F1B1B; }
            QPushButton:pressed { background-color: ##0E0C0C; }
            QFrame#separator {
                color: #334;
            }
        """)

        # ---- root layout ---------------------------------------------
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ---- LEFT: cámara + estado -----------------------------------
        left = QVBoxLayout()
        left.setSpacing(6)

        title = QLabel("Camera")
        title.setObjectName("title")
        left.addWidget(title)

        self._camera_label = QLabel()
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setMinimumSize(620, 420)
        self._camera_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._camera_label.setStyleSheet(
            "background:#000; border-radius:6px; border:1px solid #334;"
        )
        left.addWidget(self._camera_label, stretch=1)

        # Buffer de estados (mini chips)
        buf_row = QHBoxLayout()
        buf_row.addWidget(QLabel("Buffer:"))
        self._buf_labels: list[QLabel] = []
        for _ in range(6):
            lbl = QLabel("---")
            lbl.setFixedWidth(44)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "background:#2C2C33; border-radius:3px; padding:1px 2px; font-size:10px;"
            )
            buf_row.addWidget(lbl)
            self._buf_labels.append(lbl)
        buf_row.addStretch()
        left.addLayout(buf_row)

        root.addLayout(left, stretch=3)

        # ---- RIGHT: info + log ---------------------------------------
        right = QVBoxLayout()
        right.setSpacing(8)

        right.addWidget(QLabel("Estado"))

        self._state_label = QLabel(HandState.NO_HANDS.value)
        self._state_label.setObjectName("state_label")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self._state_label)

        self._raw_label = QLabel("Raw: — (0.0%)")
        self._raw_label.setObjectName("raw_label")
        self._raw_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self._raw_label)

        self._conf_bar = _ConfidenceBar()
        right.addWidget(self._conf_bar)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        right.addWidget(sep)

        right.addWidget(QLabel("Console log"))
        self._log = QTextEdit()
        self._log.setObjectName("log")
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(200)
        right.addWidget(self._log)

        right.addStretch()

        hide_btn = QPushButton("Close window")
        hide_btn.clicked.connect(self.hide)
        right.addWidget(hide_btn)

        root.addLayout(right, stretch=1)

    # ------------------------------------------------------------------
    # Slots llamados desde CameraWorker via señales
    # ------------------------------------------------------------------
    def on_frame(self, frame: np.ndarray) -> None:
        """Recibe un frame BGR y lo muestra con overlay HUD."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.flip(frame_rgb, 1)

        # Overlay HUD encima del frame
        self._draw_hud(frame_rgb)

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
        """Actualiza labels de estado y barra de confianza."""
        self._stable_state = stable
        self._raw_state    = raw
        self._confidence   = confidence

        self._state_buffer.append(stable)

        # Estado estable — color dinámico
        color = _qcolor(stable)
        self._state_label.setText(stable.value)
        self._state_label.setStyleSheet(
            f"font-size:22px; font-weight:bold; padding:6px 12px; border-radius:6px;"
            f"background:#2C2C33; color: rgb({color.red()},{color.green()},{color.blue()});"
        )

        # Raw + confianza
        opacity = "color:#aaa;" if confidence >= 0.6 else "color:#555;"
        self._raw_label.setStyleSheet(f"font-size:12px; padding:2px 0; {opacity}")
        self._raw_label.setText(f"Raw: {raw.value}  ({confidence*100:.1f}%)")

        # Barra de confianza
        self._conf_bar.set_value(confidence)

        # Buffer chips
        buf_list = list(self._state_buffer)
        for i, lbl in enumerate(self._buf_labels):
            if i < len(buf_list):
                s = buf_list[i]
                c = _qcolor(s)
                lbl.setText(s.value[:3])
                lbl.setStyleSheet(
                    f"background: rgba({c.red()},{c.green()},{c.blue()},60);"
                    f"color: rgb({c.red()},{c.green()},{c.blue()});"
                    f"border-radius:3px; padding:1px 2px; font-size:10px;"
                )
            else:
                lbl.setText("---")
                lbl.setStyleSheet(
                    "background:#2C2C33; border-radius:3px;"
                    "padding:1px 2px; font-size:10px; color:#555;"
                )

    def on_event(self, event: GestureEvent) -> None:
        """Agrega evento al log."""
        self._log.append(f"▸ {event.value}")
        # Scroll al final
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_status(self, msg: str) -> None:
        """Mensajes de sistema/debug al log."""
        if msg.startswith("[EVENT]") or msg.startswith("[STATE]"):
            self._log.append(f"<span style='color:#6699cc'>{msg}</span>")
        elif msg.startswith("[ERROR]"):
            self._log.append(f"<span style='color:#ff6b6b'>{msg}</span>")
        else:
            self._log.append(f"<span style='color:#555'>{msg}</span>")

    # ------------------------------------------------------------------
    # HUD overlay dibujado sobre el frame numpy
    # ------------------------------------------------------------------
    def _draw_hud(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        r, g, b = _STATE_COLORS.get(self._stable_state, _DEFAULT_COLOR)

        # Línea divisoria central
        cv2.line(frame, (w//2, 0), (w//2, h), (60, 60, 80), 1)

        # Estado estable (grande)
        cv2.putText(frame, self._stable_state.value,
                    (14, 44), cv2.FONT_HERSHEY_DUPLEX, 1.1, (r, g, b), 2)

        # Raw + confianza (pequeño)
        conf_color = (160, 160, 160) if self._confidence >= 0.6 else (80, 80, 80)
        cv2.putText(
            frame,
            f"Raw: {self._raw_state.value}  ({self._confidence*100:.1f}%)",
            (14, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.52, conf_color, 1,
        )

        # Buffer (chips de texto)
        buf_list = list(self._state_buffer)
        x_off = 14
        cv2.putText(frame, "Buffer:", (x_off, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 80, 100), 1)
        x_off += 62
        for s in buf_list:
            cr, cg, cb = _STATE_COLORS.get(s, _DEFAULT_COLOR)
            cv2.putText(frame, s.value[:3], (x_off, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (cr, cg, cb), 1)
            x_off += 42

        # Indicador de confianza (barra horizontal simple)
        bar_w = int(w * 0.25 * min(self._confidence, 1.0))
        cv2.rectangle(frame, (14, 108), (int(w * 0.25) + 14, 116), (30, 30, 50), -1)
        cv2.rectangle(frame, (14, 108), (14 + bar_w, 116), (r, g, b), -1)

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        """Interceptar cierre de ventana → solo ocultar, no destruir."""
        event.ignore()
        self.hide()


# ---- Widget auxiliar: barra de confianza ----------------------------

class _ConfidenceBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self.setFixedHeight(12)

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fondo
        p.setBrush(QBrush(QColor(30, 30, 50)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 4, 4)

        # Relleno
        fill_w = int(w * self._value)
        if self._value >= 0.75:
            color = QColor(80, 200, 120)
        elif self._value >= 0.60:
            color = QColor(200, 180, 60)
        else:
            color = QColor(180, 60, 60)
        p.setBrush(QBrush(color))
        p.drawRoundedRect(0, 0, fill_w, h, 4, 4)
        p.end()
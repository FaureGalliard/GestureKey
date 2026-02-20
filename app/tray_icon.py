"""
tray_icon.py — genera el ícono del system tray programáticamente.
No depende de archivos de imagen externos.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont


def make_tray_icon(active: bool = True) -> QIcon:
    """
    Dibuja un ícono de mano estilizado de 64×64 px.
    active=True  → verde (pipeline corriendo)
    active=False → gris  (detenido)
    """
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Círculo de fondo
    bg_color = QColor("#1a1a2e")
    p.setBrush(QBrush(bg_color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    # Ícono de mano / gesto (puntos y líneas que evocan landmarks)
    hand_color = QColor("#80ff9e") if active else QColor("#607080")
    accent     = QColor("#a0c4ff") if active else QColor("#445566")

    pen = QPen(hand_color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(QBrush(hand_color))

    # Palma (rectángulo redondeado)
    p.drawRoundedRect(20, 34, 24, 18, 5, 5)

    # Dedos (5 líneas verticales)
    finger_xs = [22, 27, 32, 37, 42]
    heights   = [20, 14, 12, 14, 18]
    for x, dh in zip(finger_xs, heights):
        p.drawLine(x, 34, x, 34 - dh)
        p.drawEllipse(x - 2, 34 - dh - 4, 4, 4)

    # Punto de muñeca (landmark)
    p.setBrush(QBrush(accent))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(28, 50, 8, 8)

    p.end()
    return QIcon(pix)


def make_status_icon(state_name: str) -> QIcon:
    """
    Ícono pequeño con el color del estado actual, para el tooltip del tray.
    """
    _COLORS = {
        "PALM":          "#50dc50",
        "FIST":          "#dc3c3c",
        "PINCH":         "#c83cc8",
        "TWO_FINGERS":   "#dcc828",
        "THREE_FINGERS": "#28c8dc",
        "FOUR_FINGERS":  "#dc8c28",
        "UNKNOWN":       "#888888",
        "NO HANDS":      "#444444",
    }
    color_hex = _COLORS.get(state_name, "#888888")

    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fondo
    p.setBrush(QBrush(QColor("#1a1a2e")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    # Círculo de color de estado
    p.setBrush(QBrush(QColor(color_hex)))
    p.drawEllipse(12, 12, 40, 40)

    # Iniciales del estado
    p.setPen(QPen(QColor("#ffffff")))
    font = QFont("Segoe UI", 10, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, state_name[:3])

    p.end()
    return QIcon(pix)